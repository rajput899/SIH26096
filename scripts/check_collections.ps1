# Current-source workflow acceptance using existing images; no build or service restart.
# First create frontend/work-collections-final-next with the documented production-build command.
param([string]$BrowserExecutable='C:/Program Files/Google/Chrome/Application/chrome.exe')
$ErrorActionPreference='Stop'
$taskRoot=(Get-Location).Path
if (-not (Test-Path 'frontend/work-collections-final-next/BUILD_ID')) { throw 'Validated production build is missing.' }
function Invoke-DockerChecked {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw 'Docker validation command failed.' }
}
$apiName='sih26096-collections-fixture'
$webName='sih26096-collections-workflow'
$authFile=Join-Path $taskRoot 'work/collections-e2e-auth.json'
$pdfFile=Join-Path $taskRoot 'work/collections-e2e.pdf'
$apiStarted=$false
$webStarted=$false
try {
    Invoke-DockerChecked compose run --rm --no-deps -d --name $apiName -e PROCESSING_E2E=1 -e RUN_AI_ACCEPTANCE=0 -v "${taskRoot}/backend/app:/app/app:ro" -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -u -m tests.serve_archive_e2e
    $apiStarted=$true
    $ready=$false
    for($attempt=0;$attempt -lt 30;$attempt++) {
        & docker exec $apiName python -c "import urllib.request;urllib.request.urlopen('http://localhost:8011/health/live',timeout=2)" 2>$null
        if($LASTEXITCODE -eq 0){$ready=$true;break}
        Start-Sleep -Seconds 1
    }
    if(-not $ready){throw 'Isolated API not ready.'}
    Invoke-DockerChecked exec $apiName python -c "import sys;sys.path.insert(0,'tests');from test_processing import scanned_fixture;from pathlib import Path;Path('/tmp/collections-e2e.pdf').write_bytes(scanned_fixture())"
    Invoke-DockerChecked cp "${apiName}:/tmp/archive-e2e-auth.json" $authFile
    Invoke-DockerChecked cp "${apiName}:/tmp/collections-e2e.pdf" $pdfFile
    Invoke-DockerChecked compose run --rm --no-deps -d --name $webName -p 127.0.0.1:3003:3000 -e "BACKEND_INTERNAL_URL=http://${apiName}:8011" -v "${taskRoot}/frontend/work-collections-final-next:/app/.next:ro" frontend npm run start
    $webStarted=$true
    $ready=$false
    for($attempt=0;$attempt -lt 30;$attempt++) {
        try {$null=Invoke-WebRequest 'http://localhost:3003/staff' -TimeoutSec 3;$ready=$true;break}
        catch {Start-Sleep -Seconds 1}
    }
    if(-not $ready){throw 'Isolated production frontend not ready.'}
    $env:PLAYWRIGHT_BASE_URL='http://localhost:3003'
    $env:ARCHIVE_E2E_BROWSER=$BrowserExecutable
    $env:ARCHIVE_E2E_AUTH_FILE=$authFile
    $env:PROCESSING_E2E_PDF=$pdfFile
    & node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/archive.spec.ts frontend/tests/processing.spec.ts frontend/tests/kiosk.spec.ts frontend/tests/heritage.spec.ts --output work/collections-workflow-results --workers=1
    if($LASTEXITCODE -ne 0){throw 'Current-source workflow tests failed.'}
} finally {
    if($webStarted){& docker stop $webName}
    # SIGINT lets the existing fixture server remove only its temporary schema/storage.
    if($apiStarted){& docker kill --signal SIGINT $apiName}
    Remove-Item Env:PLAYWRIGHT_BASE_URL,Env:ARCHIVE_E2E_BROWSER,Env:ARCHIVE_E2E_AUTH_FILE,Env:PROCESSING_E2E_PDF -ErrorAction SilentlyContinue
}
