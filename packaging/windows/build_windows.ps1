$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root

$Version = (Get-Content (Join-Path $Root 'VERSION') -Raw).Trim()
$ReleaseDir = Join-Path $Root 'release\windows'
$DistDir = Join-Path $Root 'dist\COMPELEC-ONE-Business'

if (Test-Path $ReleaseDir) { Remove-Item $ReleaseDir -Recurse -Force }
New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install 'pyinstaller>=6.10,<7'

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --name COMPELEC-ONE-Business `
  --collect-all streamlit `
  --collect-all altair `
  --collect-all pydeck `
  --add-data 'streamlit_v03.py;.' `
  --add-data 'architecture.py;.' `
  --add-data 'embedding.py;.' `
  --add-data 'postgres_migrations.py;.' `
  --add-data 'postgres_repository.py;.' `
  --add-data 'support_service.py;.' `
  --add-data 'v03_runtime.py;.' `
  --add-data 'knowledge_ai.py;.' `
  --add-data 'backup_restore.py;.' `
  --add-data 'migrations\postgres;migrations\postgres' `
  launch_compelec_one.py

if (-not (Test-Path (Join-Path $DistDir 'COMPELEC-ONE-Business.exe'))) {
  throw 'PyInstaller EXE wurde nicht erzeugt.'
}

$PortableZip = Join-Path $ReleaseDir "COMPELEC-ONE-Business-$Version-portable.zip"
Compress-Archive -Path (Join-Path $DistDir '*') -DestinationPath $PortableZip -CompressionLevel Optimal

$Iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $Iscc) {
  $Candidates = @(
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
  )
  foreach ($Candidate in $Candidates) {
    if (Test-Path $Candidate) { $Iscc = $Candidate; break }
  }
}
if (-not $Iscc) { throw 'Inno Setup 6 (ISCC.exe) wurde nicht gefunden.' }

& $Iscc (Join-Path $Root 'packaging\windows\COMPELEC-ONE-Business.iss')

$Setup = Join-Path $ReleaseDir "COMPELEC-ONE-Business-Setup-$Version.exe"
if (-not (Test-Path $Setup)) { throw 'Inno-Setup EXE wurde nicht erzeugt.' }

$HashFile = Join-Path $ReleaseDir 'SHA256SUMS.txt'
$Artifacts = @($Setup, $PortableZip)
$Lines = foreach ($Artifact in $Artifacts) {
  $Hash = (Get-FileHash -Path $Artifact -Algorithm SHA256).Hash.ToLowerInvariant()
  "$Hash  $([IO.Path]::GetFileName($Artifact))"
}
Set-Content -Path $HashFile -Value $Lines -Encoding ascii

Write-Host "Windows-Release erstellt: $ReleaseDir"
Get-ChildItem $ReleaseDir | Format-Table Name, Length
