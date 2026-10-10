$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$workerRoot = $PSScriptRoot
$pythonPath = Join-Path $workerRoot 'venv\Scripts\python.exe'
$runtimeDir = Join-Path $workerRoot 'tmp\runtime'
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$pidPath = Join-Path $runtimeDir 'worker.pid'
if (Test-Path -LiteralPath $pidPath) {
    $workerPid = [int](Get-Content -LiteralPath $pidPath)
    $existingWorker = Get-CimInstance Win32_Process -Filter "ProcessId = $workerPid" -ErrorAction SilentlyContinue
    if ($existingWorker -and $existingWorker.CommandLine -like '*app.tasks.celery_app*' -and $existingWorker.CommandLine -like "*$workerRoot*") {
        Write-Output "Worker already running: $workerPid"
        exit 0
    }
}
$workerProcess = Start-Process -FilePath $pythonPath -WorkingDirectory $workerRoot -WindowStyle Hidden -PassThru -ArgumentList @(
    '-m','celery','-A','app.tasks.celery_app','worker','--pool=solo','--concurrency=1',
    '--queues=aide_analysis,aide_cad','--loglevel=INFO','--without-gossip','--without-mingle'
) -RedirectStandardOutput (Join-Path $runtimeDir 'worker.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'worker.stderr.log')
Set-Content -LiteralPath $pidPath -Value $workerProcess.Id
Write-Output "Started Windows solo worker: $($workerProcess.Id). Logs: $runtimeDir"
