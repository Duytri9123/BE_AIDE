$ErrorActionPreference = 'Stop'
$elRoot = $PSScriptRoot
$elRuntime = Join-Path $elRoot 'tmp\runtime'
New-Item -ItemType Directory -Path $elRuntime -Force | Out-Null
$elPidPath = Join-Path $elRuntime 'el-worker.pid'
if (Test-Path -LiteralPath $elPidPath) {
    $elPid = [int](Get-Content -LiteralPath $elPidPath)
    $elExisting = Get-CimInstance Win32_Process -Filter "ProcessId = $elPid" -ErrorAction SilentlyContinue
    if ($elExisting -and $elExisting.CommandLine -like '*app.tasks.celery_app*' -and $elExisting.CommandLine -like '*aide_el*') {
        Write-Output "EL worker already running: $elPid"
        return
    }
}
# A dedicated queue lets EL wait for CAD/analysis jobs without blocking their worker.
$elProcess = Start-Process -FilePath (Join-Path $elRoot 'venv\Scripts\python.exe') -WorkingDirectory $elRoot -WindowStyle Hidden -PassThru -ArgumentList @(
    '-m','celery','-A','app.tasks.celery_app','worker','--pool=solo','--concurrency=1',
    '--queues=aide_el','--hostname=el@%h','--loglevel=INFO','--without-gossip','--without-mingle'
) -RedirectStandardOutput (Join-Path $elRuntime 'el-worker.stdout.log') -RedirectStandardError (Join-Path $elRuntime 'el-worker.stderr.log')
Set-Content -LiteralPath $elPidPath -Value $elProcess.Id
Write-Output "Started EL background worker: $($elProcess.Id)"
