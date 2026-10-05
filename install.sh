#!/usr/bin/env bash
# 一键安装本仓库的 AI 配置：全局提示词、本仓库 skills、云端 skills 清单。
# 幂等：已就绪的项原样跳过，只补齐缺失项、修正指向错误的链接，可重复执行。
#
# 用法：克隆本仓库后执行 ./install.sh
#   AGENTS_HOME=... ./install.sh   覆盖 skills 统一目录（默认 ~/.agents，skills CLI 约定）
#   SKILLS_AGENTS=... ./install.sh 覆盖云端 skill 分发的目标 agent；默认 codex——
#   skills CLI 对 codex 等 universal agent 只写入统一目录，不改动各 harness 目录，
#   即可见性分发实现前的中性选择。设为其他值（如 zcode）会同时写入对应 harness 目录。
#
# 按 skill 配置各模型可见性的分发暂未实现。
set -u

# 从 cmd/powershell 等环境调用时 HOME 可能缺失或为 Windows 形式，先归一化
if [ -z "${HOME:-}" ] && [ -n "${USERPROFILE:-}" ]; then HOME="$USERPROFILE"; fi
if command -v cygpath >/dev/null 2>&1 && [[ "${HOME:-}" =~ ^[A-Za-z]:[\\/] ]]; then
  HOME="$(cygpath -u "$HOME")"
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_HOME="${AGENTS_HOME:-$HOME/.agents}"
CLOUD_LIST="$REPO_DIR/install/skills-cloud.list"
SKILLS_AGENTS="${SKILLS_AGENTS:-codex}"
# 大仓库（如 mattpocock/skills）在 skills CLI 默认克隆超时内拉不完，会导致安装失败
export SKILLS_CLONE_TIMEOUT_MS="${SKILLS_CLONE_TIMEOUT_MS:-600000}"

# 全局提示词映射，每项为 仓库内源文件|目标路径（相对 $HOME）
GLOBAL_PROMPTS=(
  "system/AGENTS.md|.zcode/AGENTS.md"
  "system/AGENTS.md|.codex/AGENTS.md"
  "system/AGENTS.md|.claude/CLAUDE.md"
  "system/AGENTS.md|.pi/agent/AGENTS.md"
  "system/AGENTS.md|.dsh/AGENTS.md"
  "system/AGENTS.md|.qoder-cn/AGENTS.md"
)

FAILED=0

log()  { printf '%s\n' "$*"; }
warn() { FAILED=1; printf '  ! %s\n' "$*" >&2; }
ok()   { printf '  %s\n' "$*"; }

# 输出链接指向的绝对路径；不是链接、指向无效或无法解析时返回 1。
# 兼容 MSYS 软链接与 Windows junction（后者 readlink 可能给出 Windows 形式的路径）。
resolve_link_path() {
  local target="$1" cur base
  cur="$(readlink "$target" 2>/dev/null)" || return 1
  [ -n "$cur" ] || return 1
  base="$(cd "$(dirname "$target")" && pwd -P)" || return 1
  if [ -e "$base/$cur" ] || [ -L "$base/$cur" ]; then
    (cd "$base" && cd "$(dirname "$cur")" && printf '%s/%s\n' "$(pwd -P)" "$(basename "$cur")") && return 0
  fi
  if command -v cygpath >/dev/null 2>&1; then
    cur="$(cygpath -u "$cur" 2>/dev/null)" || return 1
    if [ -e "$cur" ]; then
      (cd "$(dirname "$cur")" && printf '%s/%s\n' "$(pwd -P)" "$(basename "$cur")") && return 0
    fi
  fi
  return 1
}

# 输出路径的规范绝对路径；路径可以是文件或目录
realpath_posix() {
  local p="$1"
  if [ -d "$p" ]; then
    (cd "$p" && pwd -P) && return 0
  fi
  printf '%s/%s\n' "$(cd "$(dirname "$p")" && pwd -P)" "$(basename "$p")"
}

# 判断 target 是否为指向 source 的链接
link_points_to() {
  local resolved want
  resolved="$(resolve_link_path "$1")" || return 1
  want="$(realpath_posix "$2")" || return 1
  [ "$resolved" = "$want" ]
}

# 在 target 创建指向 source 的链接；无权限创建软链接时（Windows）降级为
# 目录 junction，仍失败则退化为复制并告警——保证安装流程不中断
make_link() {
  local source="$1" target="$2"
  if MSYS=winsymlinks:nativestrict ln -s "$source" "$target" 2>/dev/null; then return 0; fi
  if [ -d "$source" ] && command -v cmd.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
    if cmd.exe //c mklink //J "$(cygpath -w "$target")" "$(cygpath -w "$source")" >/dev/null 2>&1; then return 0; fi
  fi
  cp -R "$source" "$target"
  warn "$target 无法创建软链接，已退化为复制；仓库更新后需重跑本脚本同步"
}

install_prompts() {
  log "== 全局提示词 =="
  local entry src dest
  for entry in "${GLOBAL_PROMPTS[@]}"; do
    src="$REPO_DIR/${entry%%|*}"
    dest="$HOME/${entry#*|}"
    if [ ! -e "$src" ]; then
      warn "源文件不存在：$src"
      continue
    fi
    if link_points_to "$dest" "$src"; then
      ok "= $dest 已就绪"
      continue
    fi
    if [ -L "$dest" ]; then
      rm "$dest" && make_link "$src" "$dest" && ok "~ $dest 链接指向已修正"
      continue
    fi
    if [ -e "$dest" ]; then
      if cmp -s "$src" "$dest"; then
        rm "$dest" && make_link "$src" "$dest" && ok "~ $dest 拷贝已替换为软链接"
      else
        # 各 harness 的全局指令以仓库为单一事实源；旧文件内容可能仍有价值，原位备份后替换
        backup="$dest.bak-$(date +%Y%m%d-%H%M%S)"
        mv "$dest" "$backup" && make_link "$src" "$dest" \
          && warn "$dest 与仓库内容不同，原文件已备份为 $backup 并替换为软链接；确认无需合并后可删除备份"
      fi
      continue
    fi
    mkdir -p "$(dirname "$dest")" && make_link "$src" "$dest" && ok "+ $dest"
  done
}

install_local_skills() {
  log "== 本地 skills（软链接到仓库）=="
  if [ ! -d "$REPO_DIR/skills" ]; then
    warn "缺少 skills 目录"
    return
  fi
  mkdir -p "$AGENTS_HOME/skills"
  local src name target
  for src in "$REPO_DIR"/skills/*/; do
    [ -d "$src" ] || continue
    name="$(basename "$src")"
    src="$REPO_DIR/skills/$name"
    target="$AGENTS_HOME/skills/$name"
    if link_points_to "$target" "$src"; then
      ok "= $name 已就绪"
      continue
    fi
    if [ -L "$target" ]; then
      rm "$target" && make_link "$src" "$target" && ok "~ $name 链接指向已修正"
      continue
    fi
    if [ -e "$target" ]; then
      if diff -r "$src" "$target" >/dev/null 2>&1; then
        rm -rf "$target" && make_link "$src" "$target" && ok "~ $name 拷贝已替换为软链接"
      else
        warn "$name 在 $AGENTS_HOME/skills 下已有不同内容，跳过；如以仓库为准，请备份并删除该目录后重跑"
      fi
      continue
    fi
    make_link "$src" "$target" && ok "+ $name"
  done
}

# skill 是否已记录在 skills CLI 的全局锁文件中
cloud_lock_has() {
  local lock="$AGENTS_HOME/.skill-lock.json" wlock
  [ -f "$lock" ] || return 1
  if command -v node >/dev/null 2>&1; then
    # node.exe 不识别 MSYS 路径，且环境可能禁用参数路径转换（MSYS2_ARG_CONV_EXCL），
    # 必须显式转成 Windows 形式，否则检查恒失败、每次运行都会重装全部云端 skill
    wlock="$lock"
    command -v cygpath >/dev/null 2>&1 && wlock="$(cygpath -w "$lock")"
    if node -e "try{const l=JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'));process.exit(l.skills&&l.skills[process.argv[2]]?0:1)}catch{process.exit(1)}" "$wlock" "$1" 2>/dev/null; then
      return 0
    fi
  fi
  # node 缺失或读取失败时退化为文本匹配；skill 名为 kebab-case，可精确匹配锁内 JSON 键
  grep -q "\"$1\":" "$lock" 2>/dev/null
}

install_cloud_skills() {
  if [ ! -f "$CLOUD_LIST" ]; then
    warn "缺少云端清单 $CLOUD_LIST"
    return
  fi
  if ! command -v npx >/dev/null 2>&1; then
    warn "未找到 npx（需安装 Node.js），跳过云端 skills"
    return
  fi
  log "== 云端 skills =="
  local agent_args=()
  [ -n "$SKILLS_AGENTS" ] && agent_args=(-a "$SKILLS_AGENTS")
  local pairs
  pairs="$(mktemp)"
  local source name store_dir
  # 第一遍：校验清单、剔除已安装项，产出 <仓库>\t<skill> 待安装对
  while read -r source name; do
    # 兼容可能的 CRLF 行尾：最后一个字段会带上 \r
    source="${source%$'\r'}"
    name="${name%$'\r'}"
    case "$source" in ''|'#'*) continue ;; esac
    if [ -z "$name" ]; then
      warn "清单行缺少 skill 名：$source"
      continue
    fi
    if cloud_lock_has "$name"; then
      ok "= $name 已安装"
      continue
    fi
    # 本地 skills 以软链接占据同名目录时，云端安装会覆盖仓库内容
    store_dir="$AGENTS_HOME/skills/$name"
    if [ -L "$store_dir" ]; then
      warn "$name 与本地软链接 skill 同名冲突，跳过云端安装"
      continue
    fi
    printf '%s\t%s\n' "$source" "$name" >>"$pairs"
  done <"$CLOUD_LIST"

  # 第二遍：按仓库分组安装。skills add 每次调用都会重新拉取源仓库，
  # 逐个安装会让同一仓库被反复克隆几十次，是安装慢的主要原因
  local repo names skill_args out s
  while read -r repo; do
    [ -n "$repo" ] || continue
    skill_args=()
    names=""
    for s in $(awk -F'\t' -v r="$repo" '$1==r{print $2}' "$pairs"); do
      skill_args+=(-s "$s")
      names="${names:+$names }$s"
    done
    if out="$(npx -y skills@latest add "$repo" -g ${skill_args[@]+"${skill_args[@]}"} -y ${agent_args[@]+"${agent_args[@]}"} </dev/null 2>&1)"; then
      ok "+ $names（$repo）"
    else
      # 整组失败时无法定位具体是哪个 skill 出错，退化为逐个安装以隔离问题
      warn "整组安装失败（$repo），逐个重试：$names"
      for s in $(awk -F'\t' -v r="$repo" '$1==r{print $2}' "$pairs"); do
        if out="$(npx -y skills@latest add "$repo" -g -s "$s" -y ${agent_args[@]+"${agent_args[@]}"} </dev/null 2>&1)"; then
          ok "+ $s（$repo）"
        else
          warn "$s 安装失败（$repo）；可手动执行：npx skills@latest add $repo -g -s $s -y"
          printf '%s\n' "$out" | tail -20 >&2
        fi
      done
    fi
  done < <(awk -F'\t' '{print $1}' "$pairs" | sort -u)
  rm -f "$pairs"
}

main() {
  log "仓库：$REPO_DIR"
  log "skills 目录：$AGENTS_HOME/skills"
  install_prompts
  install_local_skills
  install_cloud_skills
  if [ "$FAILED" -ne 0 ]; then
    log "完成，但存在需要人工处理的项（见上方 ! 行）。"
    exit 1
  fi
  log "全部就绪。"
}

main "$@"
