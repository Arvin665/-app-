param(
    [string]$BackupRoot = (Join-Path $PSScriptRoot '..\backups'),
    [int]$RetentionDays = 30
)

# 依赖 Docker Compose 正在运行；脚本生成数据库 SQL 与附件压缩包，并清理过期备份。
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BackupRoot = [System.IO.Path]::GetFullPath($BackupRoot)
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null

function Invoke-DockerToFile {
    param(
        [Parameter(Mandatory = $true)][string]$Arguments,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = 'docker'
    $startInfo.Arguments = $Arguments
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    try {
        if (-not $process.Start()) { throw '无法启动 docker 进程。' }
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $copyTask = $process.StandardOutput.BaseStream.CopyToAsync($stream)
        $process.WaitForExit()
        $copyTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        $stream.Flush()
        if ($process.ExitCode -ne 0) {
            throw "docker compose 执行失败（退出码 $($process.ExitCode)）：$($stderr.Trim())"
        }
        if ($stderr.Trim()) { Write-Warning $stderr.Trim() }
    } catch {
        $failure = $_
    } finally {
        $stream.Dispose()
        $process.Dispose()
    }
    if ($failure) {
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        throw $failure
    }
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$sqlFile = Join-Path $BackupRoot "database_$stamp.sql"
$uploadFile = Join-Path $BackupRoot "uploads_$stamp.tar.gz"

Push-Location $projectRoot
try {
    Write-Host "[1/2] 导出 MySQL 全量备份..."
    $mysqlArgs = 'compose exec -T mysql sh -c "exec mysqldump -uroot -p\"$MYSQL_ROOT_PASSWORD\" --single-transaction --routines --events \"$MYSQL_DATABASE\""'
    Invoke-DockerToFile -Arguments $mysqlArgs -Path $sqlFile

    Write-Host "[2/2] 导出附件卷..."
    $uploadArgs = 'compose exec -T backend tar -czf - -C /app uploads'
    Invoke-DockerToFile -Arguments $uploadArgs -Path $uploadFile
} finally {
    Pop-Location
}

# 仅删除脚本命名规则下的过期文件，不触碰其他备份。
$cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -LiteralPath $BackupRoot -File | Where-Object {
    ($_.Name -match '^database_\d{8}_\d{6}\.sql$' -or $_.Name -match '^uploads_\d{8}_\d{6}\.tar\.gz$') -and $_.LastWriteTime -lt $cutoff
} | Remove-Item -Force

Write-Host "备份完成：$sqlFile"
Write-Host "附件备份：$uploadFile"
    $failure = $null
