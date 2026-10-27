# 通过 UAC 启动与调用者相同的 Bash，并将退出码传回原进程。
# 路径通过环境变量传递，避免空格、引号和非 ASCII 字符被命令行解析改变。
$command = '$env:INSTALL_ELEVATED = "1"; & $env:INSTALL_BASH_PATH $env:INSTALL_SCRIPT_PATH; exit $LASTEXITCODE'
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
try {
    $process = Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList '-NoProfile', '-EncodedCommand', $encoded -Verb RunAs -Wait -PassThru -ErrorAction Stop
    exit $process.ExitCode
} catch {
    exit 125
}
