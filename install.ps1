# install.ps1 —— Windows 原生安装脚本，与 install.sh 行为一致：
# 全局提示词、本仓库 skills 链接到用户级配置目录，按清单通过 skills CLI 安装云端 skills。
# 幂等：已就绪的项原样跳过，只补齐缺失项、修正指向错误的链接，可重复执行。提示信息为英文。
# 全局提示词只写入已存在的工具配置目录；目录缺失视为该工具未安装，跳过且不为它创建目录。
#
# 用法：powershell -ExecutionPolicy Bypass -File install.ps1
# 创建符号链接需要管理员权限或已开启 Windows 开发者模式；未开启时目录链接自动降级为
# junction，文件降级为复制——降级顺序与 install.sh 的 make_link 一致。
#
# 环境变量与 install.sh 相同：
#   AGENTS_HOME              覆盖 skills 统一目录（默认 $HOME\.agents，skills CLI 约定）
#   SKILLS_AGENTS            覆盖云端 skill 分发的目标 agent（默认 codex）
#   SKILLS_CLONE_TIMEOUT_MS  覆盖 skills CLI 克隆超时（默认 600000）
#
# 按 skill 配置各模型可见性的分发暂未实现。

#Requires -Version 5.1

$RepoDir = $PSScriptRoot
$AGENTS_HOME = if ($env:AGENTS_HOME) { $env:AGENTS_HOME } else { Join-Path $HOME '.agents' }
$CloudList = Join-Path $RepoDir 'install/skills-cloud.list'
$SKILLS_AGENTS = if ($env:SKILLS_AGENTS) { $env:SKILLS_AGENTS } else { 'codex' }
# 大仓库（如 mattpocock/skills）在 skills CLI 默认克隆超时内拉不完，会导致安装失败
$env:SKILLS_CLONE_TIMEOUT_MS = if ($env:SKILLS_CLONE_TIMEOUT_MS) { $env:SKILLS_CLONE_TIMEOUT_MS } else { '600000' }

# 全局提示词映射，与 install.sh 的 GLOBAL_PROMPTS 一致。
# 目标路径所在目录由对应工具自己创建，因此它的存在就代表该工具已安装：
# 目录不存在时不写入，也不替工具创建配置目录。
$GlobalPrompts = @(
    @{ Source = 'system/AGENTS.md'; Dest = '.zcode/AGENTS.md' },
    @{ Source = 'system/AGENTS.md'; Dest = '.codex/AGENTS.md' },
    @{ Source = 'system/AGENTS.md'; Dest = '.claude/CLAUDE.md' },
    @{ Source = 'system/AGENTS.md'; Dest = '.pi/agent/AGENTS.md' },
    @{ Source = 'system/AGENTS.md'; Dest = '.dsh/AGENTS.md' },
    @{ Source = 'system/AGENTS.md'; Dest = '.qoder-cn/AGENTS.md' },
    # Trae CN 的“个人规则”：新版本改读 user_rules/ 目录下的多个 md，但旧版单文件
    # user_rules.md 仍被规则服务读取；用单文件与仓库一一对应，不替换用户自建的规则目录
    @{ Source = 'system/AGENTS.md'; Dest = '.trae-cn/user_rules.md' }
)

$script:Failed = $false

# ── 日志输出 ─────────────────────────────────────────────
# 中文 Windows 控制台默认按系统 ANSI（GBK）编码输出，✓/↻ 等符号会变问号，先切到 UTF-8
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }
# 终端支持 ANSI 且未设 NO_COLOR 时输出彩色；重定向到文件或旧控制台时输出纯文本。
# 符号约定：✓ 新装 · 无变化 ↻ 重定向/替换 − 清理 ○ 跳过（工具未安装）! 告警（需人工处理）
$script:e = [char]27
$script:Color = -not $env:NO_COLOR -and -not [Console]::IsOutputRedirected -and (
    $env:WT_SESSION -or $env:TERM_PROGRAM -or $env:ConEmuANSI -eq 'ON' -or
    $env:ANSICON -or $Host.UI.SupportsVirtualTerminal)
if ($script:Color) {
    $script:Reset = "$script:e[0m"; $script:Bold = "$script:e[1m"; $script:Dim = "$script:e[2m]"
    $script:Grn = "$script:e[32m"; $script:Ylw = "$script:e[33m"; $script:Cyn = "$script:e[36m"; $script:Gry = "$script:e[90m"
} else {
    $script:Reset = ''; $script:Bold = ''; $script:Dim = ''; $script:Grn = ''; $script:Ylw = ''; $script:Cyn = ''; $script:Gry = ''
}

# 安装项分类计数，结尾汇总
$script:NInstalled = 0; $script:NUnchanged = 0; $script:NUpdated = 0; $script:NRemoved = 0; $script:NSkipped = 0; $script:NWarned = 0

function Write-Log([string]$Message) { [Console]::Out.WriteLine($Message) }

# 状态行：符号着色，正文不着色
function Format-Status([string]$Mark, [string]$Color, [string]$Message) {
    if ($script:Color) { return "  $Color$Mark$($script:Reset) $Message" }
    return "  $Mark $Message"
}

# 分区标题：── 标题 ──────，右侧横线填充到固定总宽
function Section([string]$Label) {
    $fill = [string]'─' * [Math]::Max(0, 52 - $Label.Length)
    Write-Log ''
    if ($script:Color) {
        Write-Log ("{0}{1}── {2} {3}{4}" -f $script:Bold, $script:Cyn, $Label, $fill, $script:Reset)
    } else {
        Write-Log ("── {0} {1}" -f $Label, $fill)
    }
}

function Ok([string]$Message)   { $script:NInstalled++; Write-Log (Format-Status '✓' $script:Grn $Message) }
function Keep([string]$Message) { $script:NUnchanged++; Write-Log (Format-Status '·' $script:Gry $Message) }
function Redo([string]$Message) { $script:NUpdated++; Write-Log (Format-Status '↻' $script:Cyn $Message) }
function Del([string]$Message)  { $script:NRemoved++; Write-Log (Format-Status '−' $script:Ylw $Message) }
function Skip([string]$Message) { $script:NSkipped++; Write-Log (Format-Status '○' $script:Gry $Message) }
function Warn([string]$Message) {
    $script:Failed = $true
    $script:NWarned++
    if ($script:Color) {
        [Console]::Error.WriteLine("  $($script:Bold)$($script:Ylw)!$($script:Reset) $Message")
    } else {
        [Console]::Error.WriteLine("  ! $Message")
    }
}

function Format-Count([int]$Count, [string]$Label, [string]$Color) {
    if ($script:Color) { return "$Color$Count$($script:Reset) $Label" }
    return "$Count $Label"
}

# 结尾汇总各分类计数
function Write-Summary {
    Section 'Summary'
    $parts = @(
        (Format-Count $script:NInstalled 'installed' $script:Grn),
        (Format-Count $script:NUnchanged 'unchanged' $script:Gry),
        (Format-Count $script:NUpdated 'updated' $script:Cyn),
        (Format-Count $script:NRemoved 'removed' $script:Ylw),
        (Format-Count $script:NSkipped 'skipped' $script:Gry),
        (Format-Count $script:NWarned 'warning(s)' "$($script:Bold)$($script:Ylw)")
    )
    Write-Log ('  ' + ($parts -join ' · '))
}

function Write-Verdict([string]$Mark, [string]$Color, [string]$Message) {
    if ($script:Color) { Write-Log "$($script:Bold)$Color$Mark$($script:Reset) $Message" }
    else { Write-Log "$Mark $Message" }
}

function Write-Header {
    if ($script:Color) { Write-Log "$($script:Bold)Mowon's Profile · installer$($script:Reset)" }
    else { Write-Log "Mowon's Profile · installer" }
    Write-Log ("  {0}OS{1}          windows (PowerShell {2})" -f $script:Dim, $script:Reset, $PSVersionTable.PSVersion)
    Write-Log ("  {0}Repo{1}        {2}" -f $script:Dim, $script:Reset, $RepoDir)
    Write-Log ("  {0}Skills dir{1}  {2}" -f $script:Dim, $script:Reset, (Join-Path $AGENTS_HOME 'skills'))
    if ($script:CanSymlink) {
        Write-Log ("  {0}Symlink{1}     {2}available{3}" -f $script:Dim, $script:Reset, $script:Grn, $script:Reset)
    } else {
        Write-Log ("  {0}Symlink{1}     {2}unavailable (junction for directories, copy for files){3}" -f $script:Dim, $script:Reset, $script:Ylw, $script:Reset)
    }
}

# 归一化路径用于链接指向比较：绝对化、去尾部分隔符、忽略大小写
function Get-NormalizedPath([string]$Path) {
    ([IO.Path]::GetFullPath($Path)).TrimEnd('\').ToLowerInvariant()
}

# Test-Path 对悬空链接返回 false；用父目录枚举判断链接本身是否仍占位
function Test-EntryPresent([string]$Path) {
    if (Test-Path -LiteralPath $Path) { return $true }
    $parent = [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Path))
    if (-not [IO.Directory]::Exists($parent)) { return $false }
    foreach ($entry in [IO.Directory]::EnumerateFileSystemEntries($parent, [IO.Path]::GetFileName($Path))) {
        return $true
    }
    return $false
}

# 一次性探测：无符号链接权限（非管理员且未开开发者模式）时返回 false，
# 目录链接降级 junction、文件降级复制
function Test-SymlinkCapable {
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ('install-probe-' + [IO.Path]::GetRandomFileName())
    try {
        New-Item -ItemType Directory -Path $tmp -Force | Out-Null
        $seed = Join-Path $tmp 'seed.txt'
        Set-Content -LiteralPath $seed -Value 'probe'
        New-Item -ItemType SymbolicLink -Path (Join-Path $tmp 'seed-link.txt') -Value $seed -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    } finally {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# junction 在本地 NTFS 卷上无需特权；网络盘等不支持时返回 false，目录链接按复制处理
function Test-JunctionCapable {
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ('install-probe-' + [IO.Path]::GetRandomFileName())
    try {
        New-Item -ItemType Directory -Path $tmp -Force | Out-Null
        $seed = Join-Path $tmp 'seed-dir'
        New-Item -ItemType Directory -Path $seed | Out-Null
        New-Item -ItemType Junction -Path (Join-Path $tmp 'seed-junction') -Value $seed -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    } finally {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 在 target 创建指向 source 的链接；按 符号链接 → junction（目录）→ 复制 的顺序降级，
# 返回实际方式（symlink/junction/copy）。文件没有 junction 等价物，硬链接会让仓库文件
# 与目标共享 inode、任一侧被改写都会串写，因此不做硬链接降级。
function New-Link([string]$Source, [string]$Target) {
    $parent = [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Target))
    if (-not [IO.Directory]::Exists($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    if ($script:CanSymlink) {
        try {
            New-Item -ItemType SymbolicLink -Path $Target -Value $Source -ErrorAction Stop | Out-Null
            return 'symlink'
        } catch { }
    }
    if ([IO.Directory]::Exists($Source) -and $script:CanJunction) {
        try {
            New-Item -ItemType Junction -Path $Target -Value $Source -ErrorAction Stop | Out-Null
            return 'junction'
        } catch { }
    }
    Copy-Item -LiteralPath $Source -Destination $Target -Recurse -Force
    Warn "$Target could not be created as a symbolic link; copied instead -- re-run this script to sync after repo updates"
    return 'copy'
}

# 判断 target 是否为指向 source 的符号链接或 junction
function Test-LinkTo([string]$Source, [string]$Target) {
    $item = @(Get-Item -LiteralPath $Target -Force -ErrorAction SilentlyContinue)[0]
    if (-not $item -or ($item.LinkType -ne 'SymbolicLink' -and $item.LinkType -ne 'Junction')) { return $false }
    $target = @($item.Target)[0]
    if (-not $target) { return $false }
    return (Get-NormalizedPath $target) -eq (Get-NormalizedPath $Source)
}

# 删除已存在的任意占位项。悬空链接 Get-Item 读不到，按文件、目录顺序尝试 .NET 删除：
# DeleteFileW/RemoveDirectoryW 对 reparse point 只删链接本身，不会触及目标内容
function Remove-Entry([string]$Path) {
    if (Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue) {
        Remove-Item -LiteralPath $Path -Recurse -Force
        return
    }
    try { [IO.File]::Delete($Path); return } catch { }
    try { [IO.Directory]::Delete($Path, $false) } catch { }
}

# 预测 New-Link 会采用的方式；仅用于决定内容一致的拷贝是否升级为链接，
# 避免无链接权限时每次运行都删除重拷
function Get-PredictedMode([string]$Source) {
    if ($script:CanSymlink) { return 'symlink' }
    if ([IO.Directory]::Exists($Source) -and $script:CanJunction) { return 'junction' }
    return 'copy'
}

function Get-TreeHash([string]$Path) {
    $root = (Get-Item -LiteralPath $Path -Force).FullName
    $lines = foreach ($file in (Get-ChildItem -LiteralPath $Path -Recurse -Force -File | Sort-Object FullName)) {
        '{0}:{1}' -f $file.FullName.Substring($root.Length).TrimStart('\'), (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
    $bytes = [Text.Encoding]::UTF8.GetBytes($lines -join "`n")
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash($bytes)) -replace '-', '') } finally { $sha.Dispose() }
}

# 比较仓库内容与目标内容是否一致；类型不同视为不一致（对应 install.sh 的 cmp / diff -r）
function Test-ItemsEqual([string]$Source, [string]$Target) {
    $a = Get-Item -LiteralPath $Source -Force
    $b = Get-Item -LiteralPath $Target -Force
    if ($a.PSIsContainer -ne $b.PSIsContainer) { return $false }
    if ($a.PSIsContainer) { return (Get-TreeHash $Source) -eq (Get-TreeHash $Target) }
    return (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
}

# 单个安装项的幂等决策，行为对应 install.sh：已链接即就绪；链接指向错误则重建；
# 内容一致的拷贝升级为链接（只能复制时保留现状）；内容不同按入口类型备份或跳过
function Install-Entry([string]$Source, [string]$Target, [string]$Name, [switch]$BackupOnDifferent) {
    if (Test-LinkTo $Source $Target) { Keep "$Name already in place"; return }
    if (-not (Test-EntryPresent $Target)) {
        New-Link $Source $Target | Out-Null
        Ok $Name
        return
    }
    $item = @(Get-Item -LiteralPath $Target -Force -ErrorAction SilentlyContinue)[0]
    if (-not $item -or $item.LinkType) {
        # 指向其他位置的链接，或占位但已悬空的链接（Get-Item 读不到）
        Remove-Entry $Target
        New-Link $Source $Target | Out-Null
        Redo "$Name link retargeted"
        return
    }
    if (Test-ItemsEqual $Source $Target) {
        if ((Get-PredictedMode $Source) -ne 'copy') {
            Remove-Entry $Target
            New-Link $Source $Target | Out-Null
            Redo "$Name copy replaced with link"
        } else {
            Keep "$Name up to date (copy)"
        }
        return
    }
    if (-not $BackupOnDifferent) {
        Warn "$Name already exists with different content under $([IO.Path]::GetDirectoryName($Target)); skipped -- back it up, remove it, and re-run to take the repo version"
        return
    }
    # 各 harness 的全局指令以仓库为单一事实源；旧文件内容可能仍有价值，原位备份后替换
    $backup = "$Target.bak-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Move-Item -LiteralPath $Target -Destination $backup
    New-Link $Source $Target | Out-Null
    Warn "$Name differs from repo content; original backed up to $backup and replaced with a link; delete the backup if nothing needs merging"
}

function Install-GlobalPrompts {
    Section 'Global prompts'
    foreach ($entry in $GlobalPrompts) {
        $src = Join-Path $RepoDir $entry.Source
        $dest = Join-Path $HOME $entry.Dest
        if (-not (Test-Path -LiteralPath $src)) {
            Warn "source file not found: $src"
            continue
        }
        # 配置目录由工具自己创建，脚本不代建：没有这个目录就说明该工具没装过，
        # 写入反而会凭空造出一个没人读的配置目录
        $parent = [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($dest))
        if (-not [IO.Directory]::Exists($parent)) {
            Skip "$dest skipped ($parent not found; tool not installed)"
            continue
        }
        Install-Entry -Source $src -Target $dest -Name $dest -BackupOnDifferent
    }
}

# 只清理本安装器创建的同名一级技能链接。仅在仓库 skills 目录存在时调用；
# 使用非递归 Delete 删除链接本身，不遍历 junction 或符号链接的目标。
function Remove-StaleLocalSkillLinks([string]$SkillsRoot, [string]$AgentsSkills) {
    foreach ($item in (Get-ChildItem -LiteralPath $AgentsSkills -Force)) {
        if ($item.LinkType -ne 'SymbolicLink' -and $item.LinkType -ne 'Junction') { continue }
        $linkTarget = @($item.Target)[0]
        if (-not $linkTarget) { continue }
        if (-not [IO.Path]::IsPathRooted($linkTarget)) {
            $linkTarget = Join-Path $AgentsSkills $linkTarget
        }
        $expected = Join-Path $SkillsRoot $item.Name
        if ((Get-NormalizedPath $linkTarget) -ne (Get-NormalizedPath $expected)) { continue }
        if (Test-Path -LiteralPath $linkTarget) { continue }
        try {
            if ($item.Attributes -band [IO.FileAttributes]::Directory) {
                [IO.Directory]::Delete($item.FullName, $false)
            } else {
                [IO.File]::Delete($item.FullName)
            }
            Del "$($item.Name) stale local skill link removed"
        } catch {
            Warn "could not remove stale local skill link: $($item.FullName): $_"
        }
    }
}

function Install-LocalSkills {
    Section 'Local skills (linked to the repo)'
    $skillsRoot = Join-Path $RepoDir 'skills'
    if (-not (Test-Path -LiteralPath $skillsRoot -PathType Container)) {
        Warn "missing skills directory"
        return
    }
    $agentsSkills = Join-Path $AGENTS_HOME 'skills'
    if (-not (Test-Path -LiteralPath $agentsSkills -PathType Container)) {
        New-Item -ItemType Directory -Path $agentsSkills -Force | Out-Null
    }
    Remove-StaleLocalSkillLinks -SkillsRoot $skillsRoot -AgentsSkills $agentsSkills
    foreach ($dir in (Get-ChildItem -LiteralPath $skillsRoot -Directory | Sort-Object Name)) {
        # deprecated 仅存放归档技能；一级目录直接含 SKILL.md 时才是安装项。
        if ($dir.Name -eq 'deprecated') { continue }
        if (-not (Test-Path -LiteralPath (Join-Path $dir.FullName 'SKILL.md') -PathType Leaf)) { continue }
        Install-Entry -Source $dir.FullName -Target (Join-Path $agentsSkills $dir.Name) -Name $dir.Name
    }
}

# skill 是否已记录在 skills CLI 的全局锁文件中
function Test-CloudInstalled([string]$Name) {
    $lock = Join-Path $AGENTS_HOME '.skill-lock.json'
    if (-not (Test-Path -LiteralPath $lock -PathType Leaf)) { return $false }
    try {
        $json = Get-Content -LiteralPath $lock -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $json.skills) { return $false }
        return [bool]($json.skills.PSObject.Properties[$Name])
    } catch {
        return $false
    }
}

function Install-CloudSkills {
    Section 'Cloud skills'
    if (-not (Test-Path -LiteralPath $CloudList -PathType Leaf)) {
        Warn "cloud skill list not found: $CloudList"
        return
    }
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        Warn "npx not found (Node.js required); skipping cloud skills"
        return
    }
    $agentArgs = @()
    if ($SKILLS_AGENTS) { $agentArgs = @('-a', $SKILLS_AGENTS) }
    $pairs = @()
    # 清单是无 BOM 的 UTF-8 且含中文注释；PS 5.1 默认按系统 ANSI 读取，GBK 解码还会
    # 把中文注释结尾的字节与换行符合并，导致首条数据行被并入注释行而静默丢失
    foreach ($line in (Get-Content -LiteralPath $CloudList -Encoding UTF8)) {
        $text = $line.Trim()
        if (-not $text -or $text.StartsWith('#')) { continue }
        $fields = $text -split '\s+'
        if ($fields.Count -lt 2) {
            Warn "list line missing skill name: $text"
            continue
        }
        $name = $fields[1]
        if (Test-CloudInstalled $name) {
            Keep "$name already installed"
            continue
        }
        # 本地 skills 以链接占据同名目录时，云端安装会覆盖仓库内容
        $store = Join-Path (Join-Path $AGENTS_HOME 'skills') $name
        $storeItem = @(Get-Item -LiteralPath $store -Force -ErrorAction SilentlyContinue)[0]
        if ($storeItem -and $storeItem.LinkType) {
            Warn "$name conflicts with a local linked skill of the same name; skipped cloud install"
            continue
        }
        $pairs += [pscustomobject]@{ Repo = $fields[0]; Name = $name }
    }
    # 按仓库分组安装：skills add 每次调用都会重新拉取源仓库，
    # 逐个安装会让同一仓库被反复克隆几十次，是安装慢的主要原因
    foreach ($group in ($pairs | Group-Object -Property Repo | Sort-Object -Property Name)) {
        $repo = $group.Name
        $names = @($group.Group | ForEach-Object { $_.Name })
        $skillArgs = @()
        foreach ($n in $names) { $skillArgs += @('-s', $n) }
        $joined = $names -join ' '
        $out = (& npx -y skills@latest add $repo -g @skillArgs -y @agentArgs 2>&1) | Out-String
        if ($LASTEXITCODE -eq 0) {
            Ok "$joined ($repo)"
        } else {
            # 整组失败时无法定位具体是哪个 skill 出错，退化为逐个安装以隔离问题
            Warn "group install failed ($repo); retrying one by one: $joined"
            foreach ($n in $names) {
                $out = (& npx -y skills@latest add $repo -g -s $n -y @agentArgs 2>&1) | Out-String
                if ($LASTEXITCODE -eq 0) {
                    Ok "$n ($repo)"
                } else {
                    Warn "install failed for $n ($repo); run manually: npx skills@latest add $repo -g -s $n -y"
                    ($out -split "`r?`n" | Select-Object -Last 20) | ForEach-Object { [Console]::Error.WriteLine($_) }
                }
            }
        }
    }
}

# 链接能力只与宿主机权限有关，启动时探测一次，供各安装项复用
$script:CanSymlink = Test-SymlinkCapable
$script:CanJunction = if ($script:CanSymlink) { $false } else { Test-JunctionCapable }

Write-Header
Install-GlobalPrompts
Install-LocalSkills
Install-CloudSkills
Write-Summary

if ($script:Failed) {
    Write-Verdict '✗' $script:Ylw 'done; items marked ! above need manual attention'
    exit 1
}
Write-Verdict '✓' $script:Grn 'all set'
