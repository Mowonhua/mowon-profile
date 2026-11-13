#!/bin/sh
# 全局提示词组合：把 system/AGENTS.md、清单声明的片段与 harness 专属文件拼成
# system/composed/<key>.md。组合产物是各 harness 提示词链接的实际目标，必须是普通文件：
# 软链接只能指向一个文件，无法表达多份源文件的拼接。
# 本文件只提供函数，由 install.sh 与 install/hooks/post-commit 引用。

# 通用部分，任何 harness 都包含
COMPOSE_COMMON='system/AGENTS.md'

# compose_prompt 的结果：changed / unchanged / removed / none。
# 用变量而非命令替换回传，告警和返回码才会落在调用方所在的那个 shell 里。
COMPOSE_STATUS=

# 告警出口：默认写 stderr；安装脚本在引用本文件后覆盖本函数，让缺片段计入失败项
compose_warn() {
  printf '%s\n' "$*" >&2
}

# 读清单，每项输出一行 <key>|<目标路径>|<片段，逗号分隔>；清单缺失返回 1。
# 跳过注释与空行，去掉 CR，避免 Windows 检出或编辑器改成 CRLF 后多解析出空片段。
prompts_list_entries() { # <repo>
  list="$1/install/prompts.list"
  [ -f "$list" ] || return 1
  tr -d '\r' <"$list" | while IFS= read -r line; do
    case "$line" in
      ''|'#'*) continue ;;
    esac
    printf '%s\n' "$line"
  done
}

# 原样追加文件内容，并保证内容以换行结尾，使相邻文件之间只隔一个空行
compose_append() { # <src> <dst>
  cat "$1" >>"$2" || return 1
  [ -z "$(tail -c 1 "$1")" ] || printf '\n' >>"$2"
  return 0
}

# 组合单个 harness。片段文件缺失只告警不中止：一处笔误不该让整次组合失败，
# 其余部分照常组合，缺的那部分由调用方按告警处理。
compose_prompt() { # <repo> <key> <frags>
  repo="$1" key="$2" frags="$3"
  out="$repo/system/composed/$key.md"
  COMPOSE_STATUS=none
  # 临时文件放在 system/ 下：与产物同卷，重命名是原子的；也保证没有定制时不建 composed/ 目录
  tmp="$repo/system/.compose-$key.tmp$$"
  : >"$tmp" || return 1
  compose_append "$repo/$COMPOSE_COMMON" "$tmp" || { rm -f "$tmp"; return 1; }
  # 片段按清单里的声明顺序追加，harness 专属文件最后
  parts=0
  old_ifs="$IFS"
  IFS=,
  for frag in $frags; do
    part="$repo/system/fragments/$frag.md"
    if [ -f "$part" ]; then
      printf '\n' >>"$tmp"
      compose_append "$part" "$tmp" || { rm -f "$tmp"; return 1; }
      parts=$((parts + 1))
    else
      compose_warn "fragment not found: system/fragments/$frag.md (referenced by $key)"
    fi
  done
  IFS="$old_ifs"
  if [ -f "$repo/system/harness/$key.md" ]; then
    printf '\n' >>"$tmp"
    compose_append "$repo/system/harness/$key.md" "$tmp" || { rm -f "$tmp"; return 1; }
    parts=$((parts + 1))
  fi

  # 没有定制内容时产物无意义：目标应当直接链接通用文件，遗留产物一并清掉
  if [ "$parts" -eq 0 ]; then
    rm -f "$tmp"
    if [ -f "$out" ]; then
      rm -f "$out" && COMPOSE_STATUS=removed
    fi
    return 0
  fi

  if [ -f "$out" ] && cmp -s "$out" "$tmp"; then
    rm -f "$tmp"
    COMPOSE_STATUS=unchanged
  else
    mkdir -p "$repo/system/composed" || { rm -f "$tmp"; return 1; }
    mv -f "$tmp" "$out" || { rm -f "$tmp"; return 1; }
    COMPOSE_STATUS=changed
  fi
}

# 组合清单中的全部项，并删除清单外或已不产生内容的遗留产物。
# 每项输出一行 <status> <key>，调用方据此报告；通用文件或清单缺失时返回 1。
compose_prompts() { # <repo>
  repo="$1"
  [ -f "$repo/$COMPOSE_COMMON" ] || {
    compose_warn "source file not found: $COMPOSE_COMMON"
    return 1
  }
  entries="$(prompts_list_entries "$repo")" || return 1
  # 用 heredoc 而非管道读入：管道会开子 shell，告警的计数与失败标记就传不回来
  while IFS='|' read -r key dest frags; do
    [ -n "$key" ] || continue
    compose_prompt "$repo" "$key" "$frags" || continue
    printf '%s %s\n' "$COMPOSE_STATUS" "$key"
  done <<EOF
$entries
EOF
  keys=" $(printf '%s\n' "$entries" | awk -F'|' 'NF { printf "%s ", $1 }')"
  for path in "$repo"/system/composed/*.md; do
    [ -f "$path" ] || continue
    key="$(basename "$path" .md)"
    case "$keys" in
      *" $key "*) continue ;;
    esac
    rm -f "$path" && printf 'removed %s\n' "$key"
  done
}
