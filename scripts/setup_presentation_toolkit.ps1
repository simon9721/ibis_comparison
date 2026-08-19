param(
    [switch]$SkipMathJax
)

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Deps = Join-Path $Repo ".codex_deps\presentation"
$PythonTarget = Join-Path $Deps "python"
$NodeHome = Join-Path $Deps "node"
$MathJaxDir = Join-Path $Repo "tools\presentation_kit\mathjax"

New-Item -ItemType Directory -Force $PythonTarget | Out-Null
Write-Host "Installing Python presentation dependencies..."
& py -3.14 -m pip install --disable-pip-version-check --upgrade `
    --target $PythonTarget `
    -r (Join-Path $Repo "tools\presentation_kit\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }

if (-not $SkipMathJax) {
    $NodeExe = Join-Path $NodeHome "node.exe"
    if (-not (Test-Path $NodeExe)) {
        Write-Host "Downloading the current Node.js LTS portable runtime..."
        $Index = Invoke-RestMethod "https://nodejs.org/dist/index.json"
        $Release = $Index | Where-Object { $_.lts -and ($_.files -contains "win-x64-zip") } | Select-Object -First 1
        if (-not $Release) { throw "Could not find a Windows x64 Node.js LTS release." }
        $Version = $Release.version
        $Zip = Join-Path $Deps "node-$Version-win-x64.zip"
        $Expanded = Join-Path $Deps "node-$Version-win-x64"
        Invoke-WebRequest "https://nodejs.org/dist/$Version/node-$Version-win-x64.zip" -OutFile $Zip
        Expand-Archive -LiteralPath $Zip -DestinationPath $Deps -Force
        if (Test-Path $NodeHome) { Remove-Item -LiteralPath $NodeHome -Recurse -Force }
        Move-Item -LiteralPath $Expanded -Destination $NodeHome
        Remove-Item -LiteralPath $Zip -Force
    }

    Write-Host "Installing MathJax 4 and Sharp..."
    # npm package scripts invoke `node` and `npm` by name. Put the portable
    # runtime first so Sharp's install check works without a system Node install.
    $env:PATH = "$NodeHome;$env:PATH"
    $env:npm_config_script_shell = "C:\Windows\System32\cmd.exe"
    & (Join-Path $NodeHome "npm.cmd") install --prefix $MathJaxDir --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw "MathJax dependency installation failed." }
}

Write-Host ""
Write-Host "Presentation toolkit is ready."
Write-Host 'Use: $env:PYTHONPATH = ".codex_deps/presentation/python;."'
Write-Host "Then run: py -3.14 examples/presentation_toolkit/build_demo_deck.py"
