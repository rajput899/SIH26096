# Deploy the existing Phase 3 code and verify the actual served homepage.
# No dependency reinstall, volume reset, fixture import or full Phase 3 suite.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot 'compose.yml'
function Invoke-ProjectDocker {
    # Simple function: Docker options must not bind to PowerShell common parameters.
    $dockerArgs = @($args)
    & docker compose --project-directory $projectRoot -f $composeFile @dockerArgs
    if ($LASTEXITCODE -ne 0) { throw 'Docker command failed; see output above.' }
}

# Archive visitor routes also require the already-implemented Phase 3 backend APIs.
# Refresh the worker from the same source so the existing processing flow stays compatible.
Invoke-ProjectDocker build backend frontend worker
Invoke-ProjectDocker run --rm --no-deps frontend npm run lint
Invoke-ProjectDocker run --rm --no-deps frontend npm run typecheck
Invoke-ProjectDocker run --rm --no-deps frontend npm run build
Invoke-ProjectDocker up -d --no-build --wait --wait-timeout 240 backend frontend worker

# Read the published address from Compose instead of assuming the default port.
$published = & docker compose --project-directory $projectRoot -f $composeFile port frontend 3000
if ($LASTEXITCODE -ne 0 -or -not $published) { throw 'Cannot resolve frontend address.' }
$base = 'http://' + ($published | Select-Object -First 1).Trim()
$home = Invoke-WebRequest "$base/" -UseBasicParsing -TimeoutSec 30
if ($home.StatusCode -ne 200 -or $home.Content -notmatch 'Discover a legacy' -or
    $home.Content -match '<h1[^>]*>Local foundation') {
    throw 'The actual root route is not serving the Phase 3 kiosk. Check for another server or project on this port.'
}
foreach ($route in @('ai', 'archive', 'experience')) {
    if ($home.Content -notmatch ('href="/' + $route + '"')) {
        throw "Missing homepage navigation: /$route"
    }
    $page = Invoke-WebRequest "$base/$route" -UseBasicParsing -TimeoutSec 30
    if ($page.StatusCode -ne 200) { throw "Visitor route failed: /$route" }
}
$system = Invoke-WebRequest "$base/system" -UseBasicParsing -TimeoutSec 30
if ($system.Content -notmatch 'Local foundation') { throw 'Service-health dashboard missing at /system.' }
$staff = Invoke-WebRequest "$base/staff" -UseBasicParsing -TimeoutSec 30
if ($staff.Content -notmatch 'Staff login') { throw 'Staff access page missing.' }
$catalog = Invoke-WebRequest "$base/api/archive/catalog" -UseBasicParsing -TimeoutSec 30
if ($catalog.StatusCode -ne 200) { throw 'Visitor archive API unavailable.' }
Write-Host "PASS: actual kiosk homepage and AI / ARCHIVE / EXPERIENCE routes at $base/"
Write-Host 'PASS: service health at /system, staff access at /staff, public archive API reachable'
Write-Host 'These checks do not certify real model inference or the full OCR/review regression suite.'
