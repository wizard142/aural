$ErrorActionPreference = 'Stop'
$InstallRoot = Join-Path $env:RUNNER_TEMP 'Aural-installed-test'
$Installer = (Resolve-Path 'dist\Aural-Windows-x64-Installer.exe').Path
$Process = Start-Process -FilePath $Installer -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=`"$InstallRoot`"" -Wait -PassThru
if ($Process.ExitCode -ne 0) { throw "Installer failed: $($Process.ExitCode)" }
$Shortcut = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Aural\Aural.lnk'
if (-not (Test-Path $Shortcut)) { throw 'Start-menu shortcut missing.' }
$Shell = New-Object -ComObject WScript.Shell
$Link = $Shell.CreateShortcut($Shortcut)
if ($Link.TargetPath -ne (Join-Path $InstallRoot 'Aural.exe')) { throw 'Start-menu shortcut points to wrong executable.' }
$Report = Join-Path $PWD 'smoke-result-installed.json'
$Process = Start-Process -FilePath (Join-Path $InstallRoot 'Aural.exe') -ArgumentList '--self-test','--self-test-result',"`"$Report`"" -Wait -PassThru
if ($Process.ExitCode -ne 0) { throw "Installed app test failed: $($Process.ExitCode)" }
$DataRoot = Join-Path $env:LOCALAPPDATA 'Aural'
New-Item -ItemType Directory -Force $DataRoot | Out-Null
$Marker = Join-Path $DataRoot 'uninstall-preservation-test.txt'
Set-Content $Marker 'Keep local music and preferences.'
$Process = Start-Process -FilePath (Join-Path $InstallRoot 'unins000.exe') -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait -PassThru
if ($Process.ExitCode -ne 0) { throw "Uninstall failed: $($Process.ExitCode)" }
if (Test-Path (Join-Path $InstallRoot 'Aural.exe')) { throw 'Uninstall left the app executable.' }
if (-not (Test-Path $Marker)) { throw 'Uninstall deleted user data.' }
Remove-Item $Marker
Write-Host 'Installer, Start-menu shortcut, installed app, and data-preserving uninstall passed.'
