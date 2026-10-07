param([switch]$SkipTools, [switch]$Installer)
$ErrorActionPreference = 'Stop'
$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Push-Location $AppRoot
try {
    if (-not (Test-Path '.venv-win\Scripts\python.exe')) {
        & py -3.12 -m venv .venv-win
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 first.' }
    }
    $Python = Join-Path $AppRoot '.venv-win\Scripts\python.exe'
    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
    & $Python -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    if (-not $SkipTools) {
        & $Python packaging\windows\prepare_tools.py
        if ($LASTEXITCODE -ne 0) { throw 'Tool preparation failed.' }
    }
    & $Python -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    & $Python -m piplicenses --with-license-file --format=json --output-file=vendor\notices\python-licenses.json
    if ($LASTEXITCODE -ne 0) { throw 'License inventory failed.' }
    & $Python -m PyInstaller --noconfirm --clean packaging\windows\Aural.spec
    if ($LASTEXITCODE -ne 0) { throw 'Windows application build failed.' }
    & '.\dist\Aural\Aural.exe' --download-worker --version > build\worker-version.txt
    if ($LASTEXITCODE -ne 0) { throw 'Packaged download worker failed.' }
    if (-not (Get-Content build\worker-version.txt -Raw).Trim()) { throw 'Download worker returned no version.' }
    Compress-Archive -Path dist\Aural -DestinationPath dist\Aural-Windows-x64.zip -Force
    if ($Installer) {
        $Compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($Compiler) { $CompilerPath = $Compiler.Source }
        else { $CompilerPath = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
        if (-not (Test-Path $CompilerPath)) { throw 'Install Inno Setup 6 or put ISCC.exe on PATH.' }
        & $CompilerPath packaging\windows\Aural.iss
        if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
    }
    Write-Host 'Windows output is in dist/.'
} finally { Pop-Location }
