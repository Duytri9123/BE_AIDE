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
# A stopped worker can leave its heartbeat alive for up to 20 seconds. Clear
# that stale marker before launching a replacement so the readiness wait cannot
# succeed on the previous process' signal.
& $pythonPath -c "from app.services import job_queue; c=job_queue.sync_client(); c.delete(job_queue.READY_KEY); c.close()" 2>$null
$workerProcess = Start-Process -FilePath $pythonPath -WorkingDirectory $workerRoot -WindowStyle Hidden -PassThru -ArgumentList @(
    '-m','celery','-A','app.tasks.celery_app','worker','--pool=solo','--concurrency=1',
    '--queues=aide_analysis,aide_cad','--loglevel=INFO','--without-gossip','--without-mingle'
) -RedirectStandardOutput (Join-Path $runtimeDir 'worker.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'worker.stderr.log')
Set-Content -LiteralPath $pidPath -Value $workerProcess.Id
Write-Output "Starting Windows solo worker: $($workerProcess.Id). Waiting for readiness..."

# Importing the CAD catalog can take around one minute on Windows. Do not tell
# the API launcher that the worker is ready until the Celery ready signal has
# published its Redis heartbeat.
$ready = $false
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    if ($workerProcess.HasExited) {
        throw "CAD analysis worker exited during startup. Check logs in $runtimeDir"
    }
    $readyCheck = & $pythonPath -c "from app.services import job_queue; c=job_queue.sync_client(); print('1' if c.exists(job_queue.READY_KEY) else '0'); c.close()" 2>$null
    if ($readyCheck -eq '1') {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    throw "CAD analysis worker did not become ready within 180 seconds. Check logs in $runtimeDir"
}
Write-Output "Windows solo worker ready: $($workerProcess.Id). Logs: $runtimeDir"
