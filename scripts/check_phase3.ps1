# Run from the project root in a terminal with Docker and browser subprocess access.
# Does not import any real archival material. Test schemas/files are isolated.
param([string]$BrowserExecutable = 'C:/Program Files/Google/Chrome/Application/chrome.exe', [switch]$RunAI, [switch]$SkipBackendTests, [switch]$KeepRunningServices)
$ErrorActionPreference = 'Stop'
function Invoke-CheckedDocker {
    # Keep this a simple function so Docker flags are not bound as common parameters.
    $Arguments = @($args)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed: $($Arguments[0..1] -join ' ')" }
}

if ($KeepRunningServices) {
    # Use only after verifying the running images contain the application changes.
    # This avoids interrupting ingestion or workers during independent fixture tests.
    Write-Host 'Using existing services/images; no build or service restart requested.'
} else {
    Invoke-CheckedDocker compose up -d --build --wait --wait-timeout 240 backend frontend worker
}
$aiCheck = if ($RunAI) { '1' } else { '0' }
if (-not $SkipBackendTests) {
    Invoke-CheckedDocker compose exec -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=$aiCheck backend python -m pytest -p no:cacheprovider -q
} else { Write-Host "SKIPPED backend tests by explicit flag; use the separately recorded backend result." }
Invoke-CheckedDocker compose exec backend python -m ruff check --no-cache app tests
Invoke-CheckedDocker compose exec frontend npm run lint
Invoke-CheckedDocker compose exec frontend npm run typecheck
Invoke-CheckedDocker compose run --rm --no-deps frontend npm run build

$fixtureStarted = $false
$frontendStarted = $false
$workspacePath = (Get-Location).Path
$authFile = Join-Path $workspacePath 'work/phase3-e2e-auth.json'
$fixtureFile = Join-Path $workspacePath 'work/phase3-e2e.pdf'
New-Item -ItemType Directory -Path (Join-Path $workspacePath 'work') -Force | Out-Null
try {
    Invoke-CheckedDocker compose exec -T backend python -c "import socket; s=socket.socket(); s.bind(('0.0.0.0',8011)); s.close()"
    Invoke-CheckedDocker compose exec -d -e PROCESSING_E2E=1 -e RUN_AI_ACCEPTANCE=$aiCheck backend sh -c 'exec python -u -m tests.serve_archive_e2e > /tmp/phase3-e2e-server.log 2>&1'
    $fixtureStarted = $true
    # Handle expected connection refusals inside Python, not PowerShell's error stream.
    $waitForFixture = @'
import json
import sys
import time
import urllib.request
from pathlib import Path

last_error = 'No response'
for attempt in range(30):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8011/health/live', timeout=2) as response:
            if response.status != 200 or json.load(response).get('status') != 'ok':
                raise ValueError('Unexpected health response')
        print('PASS: isolated E2E API is ready on port 8011', flush=True)
        sys.exit(0)
    except Exception as exc:
        last_error = f'{type(exc).__name__}: {exc}'
        if attempt < 29:
            time.sleep(1)

print(f'Isolated API did not become ready. Last probe error: {last_error}', flush=True)
log = Path('/tmp/phase3-e2e-server.log')
print(log.read_text(errors='replace') if log.exists() else 'No E2E server log was created.', flush=True)
sys.exit(1)
'@
    Invoke-CheckedDocker compose exec -T backend python -c $waitForFixture
    Invoke-CheckedDocker compose exec -T backend python -c "import sys;sys.path.insert(0,'tests');from test_processing import scanned_fixture;from pathlib import Path;Path('/tmp/phase3-e2e.pdf').write_bytes(scanned_fixture())"
    Invoke-CheckedDocker compose cp backend:/tmp/archive-e2e-auth.json $authFile
    Invoke-CheckedDocker compose cp backend:/tmp/phase3-e2e.pdf $fixtureFile
    Invoke-CheckedDocker compose run --rm --no-deps -d --name sih26096-phase3-browser -p 127.0.0.1:3001:3000 -e BACKEND_INTERNAL_URL=http://backend:8011 frontend
    $frontendStarted = $true
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $null = Invoke-WebRequest 'http://localhost:3001/archive' -TimeoutSec 3
            $ready = $true; break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) { throw 'Isolated frontend did not become ready' }
    $env:PLAYWRIGHT_BASE_URL = 'http://localhost:3001'
    $env:ARCHIVE_E2E_AUTH_FILE = $authFile
    $env:PROCESSING_E2E_PDF = $fixtureFile
    $env:ARCHIVE_E2E_BROWSER = $BrowserExecutable
    Push-Location frontend
    try {
        node node_modules/@playwright/test/cli.js test tests/archive.spec.ts tests/processing.spec.ts tests/kiosk.spec.ts tests/heritage.spec.ts --workers=1
        if ($LASTEXITCODE -ne 0) { throw 'Kiosk and heritage browser verification failed' }
    } finally { Pop-Location }
} finally {
    if ($fixtureStarted) {
        & docker compose exec -T backend python -c "import json,os,signal;from pathlib import Path;p=Path('/tmp/archive-e2e-auth.json');os.kill(json.loads(p.read_text())['pid'],signal.SIGINT) if p.exists() else None"
    }
    if ($frontendStarted) { & docker stop sih26096-phase3-browser }
    & docker compose exec -T backend python -c "from pathlib import Path;Path('/tmp/phase3-e2e.pdf').unlink(missing_ok=True)"
    Remove-Item -LiteralPath $authFile, $fixtureFile -Force -ErrorAction SilentlyContinue
    Remove-Item Env:ARCHIVE_E2E_AUTH_FILE, Env:PROCESSING_E2E_PDF, Env:ARCHIVE_E2E_BROWSER, Env:PLAYWRIGHT_BASE_URL -ErrorAction SilentlyContinue
}

if ($RunAI) { Write-Host 'PASS: Kiosk and heritage automated runtime suite, including real Ollama/Qdrant acceptance' } else { Write-Host 'PASS: Kiosk and heritage baseline runtime suite. Real model acceptance NOT RUN; repeat with -RunAI after configuring installed models.' }
Write-Host 'Manual acceptance still required: listen to local speech, screen-reader navigation, touch hardware and legitimate archival source questions.'

