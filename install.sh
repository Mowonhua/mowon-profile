#!/usr/bin/env bash
# 一键安装本仓库的 AI 配置：全局提示词、本仓库 skills、云端 skills 清单。
# 幂等：已就绪的项原样跳过，只补齐缺失项、修正指向错误的链接，可重复执行。
#
# 用法：克隆本仓库后执行 ./install.sh（macOS / Linux 原生支持，Windows 在 Git Bash / MSYS2
#       中执行；Windows 原生环境可改用行为一致的 install.ps1）。
#   AGENTS_HOME=... ./install.sh   覆盖 skills 统一目录（默认 ~/.agents，skills CLI 约定）
#   SKILLS_AGENTS=... ./install.sh 覆盖云端 skill 分发的目标 agent；默认 codex——
#   skills CLI 对 codex 等 universal agent 只写入统一目录，不改动各 harness 目录，
#   即可见性分发实现前的中性选择。设为其他值（如 zcode）会同时写入对应 harness 目录。
#
# 按 skill 配置各模型可见性的分发暂未实现。
set -u

# 用 sh/dash/zsh 等调用时缺少本脚本依赖的 bash 特性（数组、进程替换），转交 bash 重新执行
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi

# 检测宿主 OS；windows 指 MSYS/Cygwin 等 POSIX 层，链接降级与路径归一化仅在该分支生效
case "$(uname -s)" in
  Darwin) OS=darwin ;;
  Linux) OS=linux ;;
  MINGW*|MSYS*|CYGWIN*|Windows*) OS=windows ;;
  *) OS=unix ;;
esac

if [ "$OS" = windows ]; then
  # 从 cmd/powershell 等环境调用时 HOME 可能缺失或为 Windows 形式，先归一化
  if [ -z "${HOME:-}" ] && [ -n "${USERPROFILE:-}" ]; then HOME="$USERPROFILE"; fi
  if command -v cygpath >/dev/null 2>&1 && [[ "${HOME:-}" =~ ^[A-Za-z]:[\\/] ]]; then
    HOME="$(cygpath -u "$HOME")"
  fi
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

# ── 日志输出 ─────────────────────────────────────────────────────────
# 颜色仅在 stdout 接终端且未设 NO_COLOR 时启用；重定向到文件时输出纯文本。
# 符号约定：✓ 新装 · 无变化 ↻ 重定向/替换 − 清理 ! 告警（需人工处理）
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  R=$'\033[0m' B=$'\033[1m' DIM=$'\033[2m'
  GRN=$'\033[32m' YLW=$'\033[33m' CYN=$'\033[36m' GRY=$'\033[90m'
else
  R='' B='' DIM='' GRN='' YLW='' CYN='' GRY=''
fi

# 安装项分类计数，main 结尾汇总
N_INSTALLED=0; N_UNCHANGED=0; N_UPDATED=0; N_REMOVED=0; N_WARNED=0

# 分区标题：── 标题 ──────，右侧横线填充到固定总宽
section() {
  local label="$*" fill='' i
  for ((i = ${#label} + 4; i < 56; i++)); do fill+="─"; done
  printf '\n%s── %s %s%s\n' "$B$CYN" "$label" "$fill" "$R"
}
ok()   { N_INSTALLED=$((N_INSTALLED+1)); printf '  %s✓%s %s\n' "$GRN" "$R" "$*"; }
keep() { N_UNCHANGED=$((N_UNCHANGED+1)); printf '  %s·%s %s\n' "$GRY" "$R" "$*"; }
redo() { N_UPDATED=$((N_UPDATED+1)); printf '  %s↻%s %s\n' "$CYN" "$R" "$*"; }
del()  { N_REMOVED=$((N_REMOVED+1)); printf '  %s−%s %s\n' "$YLW" "$R" "$*"; }
warn() { N_WARNED=$((N_WARNED+1)); FAILED=1; printf '  %s!%s %s\n' "$B$YLW" "$R" "$*" >&2; }

# 结尾汇总各分类计数
summary() {
  section 'Summary'
  printf '  %s%s%s installed · %s%s%s unchanged · %s%s%s updated · %s%s%s removed · %s%s%s warning(s)\n' \
    "$GRN" "$N_INSTALLED" "$R" "$GRY" "$N_UNCHANGED" "$R" "$CYN" "$N_UPDATED" "$R" \
    "$YLW" "$N_REMOVED" "$R" "$B$YLW" "$N_WARNED" "$R"
}

# 探测当前环境能否创建软链接。Cygwin 默认会用“复制”冒充 ln -s，MSYS 亦然，
# 必须显式 nativestrict 才能得到真实链接或失败；非 Windows 上这些变量无效果、恒成功。
# Windows 无特权（未开开发者模式）时返回 1，此时文件链接不可用，
# 内容一致的旧拷贝保持原样，避免每次运行都删除重拷。
can_symlink() {
  local d rc
  d="$(mktemp -d)" && : >"$d/probe-target" || return 1
  MSYS=winsymlinks:nativestrict CYGWIN=winsymlinks:nativestrict \
    ln -s "$d/probe-target" "$d/probe-link" 2>/dev/null
  rc=$?
  rm -rf "$d"
  return "$rc"
}

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
  if MSYS=winsymlinks:nativestrict CYGWIN=winsymlinks:nativestrict ln -s "$source" "$target" 2>/dev/null; then return 0; fi
  if [ "$OS" = windows ] && [ -d "$source" ] \
     && command -v cmd.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
    if cmd.exe //c mklink //J "$(cygpath -w "$target")" "$(cygpath -w "$source")" >/dev/null 2>&1; then return 0; fi
  fi
  cp -R "$source" "$target"
  warn "$target could not be created as a symbolic link; copied instead -- re-run this script to sync after repo updates"
}

install_prompts() {
  section "Global prompts"
  local entry src dest backup
  for entry in "${GLOBAL_PROMPTS[@]}"; do
    src="$REPO_DIR/${entry%%|*}"
    dest="$HOME/${entry#*|}"
    if [ ! -e "$src" ]; then
      warn "source file not found: $src"
      continue
    fi
    if link_points_to "$dest" "$src"; then
      keep "$dest already in place"
      continue
    fi
    if [ -L "$dest" ]; then
      rm "$dest" && make_link "$src" "$dest" && redo "$dest link retargeted"
      continue
    fi
    if [ -e "$dest" ]; then
      if cmp -s "$src" "$dest"; then
        if [ "$CAN_SYMLINK" -eq 1 ]; then
          rm "$dest" && make_link "$src" "$dest" && redo "$dest copy replaced with link"
        else
          keep "$dest up to date (copy)"
        fi
      else
        # 各 harness 的全局指令以仓库为单一事实源；旧文件内容可能仍有价值，原位备份后替换
        backup="$dest.bak-$(date +%Y%m%d-%H%M%S)"
        mv "$dest" "$backup" && make_link "$src" "$dest" \
          && warn "$dest differs from repo content; original backed up to $backup and replaced with a link; delete the backup if nothing needs merging"
      fi
      continue
    fi
    mkdir -p "$(dirname "$dest")" && make_link "$src" "$dest" && ok "$dest"
  done
}

# 只清理本安装器创建的同名一级技能链接。父目录必须仍可解析，避免把
# 仓库不可访问误判为技能已删除；rm 不递归、不带尾斜杠，只删除链接本身。
cleanup_stale_local_skills() {
  local root target raw parent resolved expected
  root="$(cd "$REPO_DIR/skills" && pwd -P)" || return
  for target in "$AGENTS_HOME"/skills/*; do
    [ -L "$target" ] && [ ! -e "$target" ] || continue
    raw="$(readlink "$target")" || continue
    if [ "$OS" = windows ] && command -v cygpath >/dev/null 2>&1; then
      raw="$(cygpath -u "$raw")" || continue
    fi
    case "$raw" in /*) ;; *) raw="$(dirname "$target")/$raw" ;; esac
    raw="${raw%/}"
    parent="$(cd "$(dirname "$raw")" 2>/dev/null && pwd -P)" || continue
    resolved="$parent/$(basename "$raw")"
    expected="$root/$(basename "$target")"
    if [ "$OS" = windows ]; then
      resolved="$(printf '%s' "$resolved" | tr '[:upper:]' '[:lower:]')"
      expected="$(printf '%s' "$expected" | tr '[:upper:]' '[:lower:]')"
    fi
    [ "$resolved" = "$expected" ] || continue
    if rm -- "$target"; then
      del "$(basename "$target") stale local skill link removed"
    else
      warn "could not remove stale local skill link: $target"
    fi
  done
}

install_local_skills() {
  section "Local skills (linked to the repo)"
  if [ ! -d "$REPO_DIR/skills" ]; then
    warn "missing skills directory"
    return
  fi
  mkdir -p "$AGENTS_HOME/skills"
  cleanup_stale_local_skills
  local src name target
  for src in "$REPO_DIR"/skills/*/; do
    [ -d "$src" ] || continue
    name="$(basename "$src")"
    # deprecated 仅存放归档技能；一级目录直接含 SKILL.md 时才是安装项。
    [ "$name" = deprecated ] && continue
    [ -f "$src/SKILL.md" ] || continue
    src="$REPO_DIR/skills/$name"
    target="$AGENTS_HOME/skills/$name"
    if link_points_to "$target" "$src"; then
      keep "$name already in place"
      continue
    fi
    if [ -L "$target" ]; then
      rm "$target" && make_link "$src" "$target" && redo "$name link retargeted"
      continue
    fi
    if [ -e "$target" ]; then
      if diff -r "$src" "$target" >/dev/null 2>&1; then
        rm -rf "$target" && make_link "$src" "$target" && redo "$name copy replaced with link"
      else
        warn "$name already exists with different content under $AGENTS_HOME/skills; skipped -- back it up, remove it, and re-run to take the repo version"
      fi
      continue
    fi
    make_link "$src" "$target" && ok "$name"
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
  section "Cloud skills"
  if [ ! -f "$CLOUD_LIST" ]; then
    warn "cloud skill list not found: $CLOUD_LIST"
    return
  fi
  if ! command -v npx >/dev/null 2>&1; then
    warn "npx not found (Node.js required); skipping cloud skills"
    return
  fi
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
      warn "list line missing skill name: $source"
      continue
    fi
    if cloud_lock_has "$name"; then
      keep "$name already installed"
      continue
    fi
    # 本地 skills 以软链接占据同名目录时，云端安装会覆盖仓库内容
    store_dir="$AGENTS_HOME/skills/$name"
    if [ -L "$store_dir" ]; then
      warn "$name conflicts with a local linked skill of the same name; skipped cloud install"
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
      ok "$names ($repo)"
    else
      # 整组失败时无法定位具体是哪个 skill 出错，退化为逐个安装以隔离问题
      warn "group install failed ($repo); retrying one by one: $names"
      for s in $(awk -F'\t' -v r="$repo" '$1==r{print $2}' "$pairs"); do
        if out="$(npx -y skills@latest add "$repo" -g -s "$s" -y ${agent_args[@]+"${agent_args[@]}"} </dev/null 2>&1)"; then
          ok "$s ($repo)"
        else
          warn "install failed for $s ($repo); run manually: npx skills@latest add $repo -g -s $s -y"
          printf '%s\n' "$out" | tail -n 20 >&2
        fi
      done
    fi
  done < <(awk -F'\t' '{print $1}' "$pairs" | sort -u)
  rm -f "$pairs"
}

CAN_SYMLINK=0; can_symlink && CAN_SYMLINK=1

main() {
  local title="Mowon's Profile · installer"
  printf '%s%s%s\n' "$B" "$title" "$R"
  printf '  %sOS%s          %s\n' "$DIM" "$R" "$OS"
  printf '  %sRepo%s        %s\n' "$DIM" "$R" "$REPO_DIR"
  printf '  %sSkills dir%s  %s\n' "$DIM" "$R" "$AGENTS_HOME/skills"
  if [ "$CAN_SYMLINK" -eq 1 ]; then
    printf '  %sSymlink%s     %savailable%s\n' "$DIM" "$R" "$GRN" "$R"
  else
    printf '  %sSymlink%s     %sunavailable (junction for directories, copy for files)%s\n' "$DIM" "$R" "$YLW" "$R"
  fi
  install_prompts
  install_local_skills
  install_cloud_skills
  summary
  if [ "$FAILED" -ne 0 ]; then
    printf '%s✗ done; items marked %s!%s above need manual attention%s\n' "$YLW" "$R$YLW" "$B$YLW" "$R"
    exit 1
  fi
  printf '%s✓ all set%s\n' "$B$GRN" "$R"
}

main "$@"
