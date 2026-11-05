$ErrorActionPreference = 'Stop'
$backendRoot = Split-Path -Parent $PSScriptRoot
$ocrRuntime = Join-Path $backendRoot '.venv-ocr'
if (-not (Test-Path (Join-Path $ocrRuntime 'Scripts/python.exe'))) {
    py -3.13 -m venv $ocrRuntime
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.13 before creating the OCR runtime.' }
}
& (Join-Path $ocrRuntime 'Scripts/python.exe') -m pip install -r (Join-Path $backendRoot 'requirements-ocr.txt')
if ($LASTEXITCODE -ne 0) { throw 'OCR package installation failed.' }
Write-Host 'OCR runtime installed. First OCR call downloads the recognition models.'
