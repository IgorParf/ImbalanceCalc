<#
.SYNOPSIS
    Збірка ImbalanceCalc у Windows-додаток.

.DESCRIPTION
    Готує іконку та ресурс версії, запускає PyInstaller зі специфікацією
    installer/imbalance_calc.spec, за потреби збирає інсталятор Inno Setup.

    Результати:
        dist\ImbalanceCalc\ImbalanceCalc.exe          застосунок (one-folder)
        dist\ImbalanceCalc-<версія>-setup.exe          інсталятор (-Installer)

.PARAMETER Clean
    Видалити build\ і dist\ перед збіркою.

.PARAMETER Installer
    Після збірки скомпілювати інсталятор. Потрібен Inno Setup 6 (ISCC.exe).

.PARAMETER SkipApp
    Не перезбирати застосунок — лише інсталятор з наявної dist\ImbalanceCalc.

.EXAMPLE
    .\installer\build.ps1
    .\installer\build.ps1 -Clean -Installer
    .\installer\build.ps1 -SkipApp -Installer
#>
param(
    [switch]$Clean,
    [switch]$Installer,
    [switch]$SkipApp
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"

function Invoke-Native {
    <#
        Запустити зовнішню програму та перевірити код повернення.

        У Windows PowerShell 5.1 при $ErrorActionPreference = "Stop" будь-який
        рядок, який нативна програма пише у stderr, стає термінальною помилкою.
        PyInstaller і ISCC пишуть туди звичайні INFO-повідомлення, тому на час
        виклику знижуємо рівень реакції та орієнтуємося лише на $LASTEXITCODE.
    #>
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$FailureMessage = "Зовнішня програма завершилася з помилкою"
    )

    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $FilePath @Arguments
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }
    if ($code -ne 0) { throw "$FailureMessage (код $code)" }
}

function Find-Iscc {
    <#  Компілятор Inno Setup: спочатку в PATH, далі у стандартних місцях.  #>
    $command = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    return $null
}

if (-not (Test-Path $python)) {
    throw "Не знайдено інтерпретатор $python. Створіть venv і встановіть залежності."
}

$ErrorActionPreference = "Continue"
$version = (& $python -c "import sys; sys.path.insert(0, r'$root\src'); import imbalance_calc; print(imbalance_calc.__version__)")
$versionCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($versionCode -ne 0 -or -not $version) { throw "Не вдалося визначити версію застосунку" }
$version = "$version".Trim()
Write-Host "Версія: $version" -ForegroundColor Cyan

if (-not $SkipApp) {
    Write-Host "Перевірка залежностей збірки..." -ForegroundColor Cyan
    Invoke-Native $python @("-m", "pip", "install", "--quiet", "--upgrade", "pyinstaller", "pywebview") `
        -FailureMessage "Не вдалося встановити pyinstaller/pywebview"

    if ($Clean) {
        Write-Host "Очищення build\ та dist\..." -ForegroundColor Cyan
        foreach ($dir in @("build", "dist")) {
            $path = Join-Path $root $dir
            if (Test-Path $path) { Remove-Item $path -Recurse -Force }
        }
    }

    # Ресурс версії має існувати ДО запуску PyInstaller, інакше .exe лишиться
    # без даних версії, а помилки не буде — просто порожні властивості файлу.
    Write-Host "Іконка та ресурс версії..." -ForegroundColor Cyan
    Invoke-Native $python @((Join-Path $root "scripts\make_icon.py")) `
        -FailureMessage "Не вдалося створити іконку"
    Invoke-Native $python @((Join-Path $root "scripts\make_version_info.py")) `
        -FailureMessage "Не вдалося створити ресурс версії"

    Write-Host "Збірка застосунку (кілька хвилин)..." -ForegroundColor Cyan
    Push-Location $root
    try {
        Invoke-Native $python @(
            "-m", "PyInstaller", "installer\imbalance_calc.spec",
            "--noconfirm", "--distpath", "dist", "--workpath", "build"
        ) -FailureMessage "PyInstaller завершився з помилкою"
    }
    finally {
        Pop-Location
    }
}

$appExe = Join-Path $root "dist\ImbalanceCalc\ImbalanceCalc.exe"
if (-not (Test-Path $appExe)) { throw "Не знайдено $appExe" }

$size = (Get-ChildItem (Join-Path $root "dist\ImbalanceCalc") -Recurse -File |
         Measure-Object Length -Sum).Sum
Write-Host ""
Write-Host ("Застосунок: {0}" -f $appExe) -ForegroundColor Green
Write-Host ("Розмір теки: {0:N0} МБ" -f ($size / 1MB))

# Сторінки лежать у збірці як дані, тому їхні імпорти PyInstaller не бачить.
# Самоперевірка імпортує все потрібне і формує пробний PDF — без неї відсутній
# модуль виявляється лише при ручному клацанні по інтерфейсу.
Write-Host ""
Write-Host "Самоперевірка збірки..." -ForegroundColor Cyan
$check = Start-Process $appExe -ArgumentList "--selfcheck" -PassThru
# .Handle треба торкнутися до очікування: без цього об'єкт від Start-Process
# не кешує дескриптор, і WaitForExit/ExitCode можуть не побачити завершення.
$null = $check.Handle
if (-not $check.WaitForExit(120000)) {
    $check.Kill()
    throw "Самоперевірка не завершилася за 2 хвилини"
}
if ($check.ExitCode -ne 0) {
    $log = Join-Path $env:LOCALAPPDATA "ImbalanceCalc\logs\desktop.log"
    if (Test-Path $log) { Get-Content $log -Tail 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor Red } }
    throw "Самоперевірка збірки провалена (код $($check.ExitCode)). Подробиці: $log"
}
Write-Host "Самоперевірка пройдена." -ForegroundColor Green

if ($Installer) {
    $iscc = Find-Iscc
    if (-not $iscc) {
        throw @"
Не знайдено ISCC.exe (компілятор Inno Setup 6).
Встановіть Inno Setup і повторіть, або зберіть інсталятор пізніше:
    .\installer\build.ps1 -SkipApp -Installer
"@
    }

    Write-Host ""
    Write-Host "Збірка інсталятора ($iscc)..." -ForegroundColor Cyan
    Invoke-Native $iscc @("/DAppVersion=$version", (Join-Path $root "installer\setup.iss")) `
        -FailureMessage "Inno Setup завершився з помилкою"

    $setup = Join-Path $root "dist\ImbalanceCalc-$version-setup.exe"
    if (Test-Path $setup) {
        $setupSize = (Get-Item $setup).Length
        Write-Host ""
        Write-Host ("Інсталятор: {0}" -f $setup) -ForegroundColor Green
        Write-Host ("Розмір: {0:N0} МБ" -f ($setupSize / 1MB))
    }
}
else {
    $iscc = Find-Iscc
    if ($iscc) {
        Write-Host ""
        Write-Host "Inno Setup знайдено. Інсталятор: .\installer\build.ps1 -SkipApp -Installer" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "Перевірте запуск на машині без Python перед роздачею." -ForegroundColor Yellow
