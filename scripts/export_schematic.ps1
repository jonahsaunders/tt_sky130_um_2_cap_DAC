param([string]$KicadCli = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe')
$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path $PSScriptRoot -Parent
$env:KICAD_CONFIG_HOME = Join-Path $packageRoot 'build\kicad-config'
New-Item -ItemType Directory -Force $env:KICAD_CONFIG_HOME | Out-Null
$schematicPath = Join-Path $packageRoot 'schematic\suarez_dac.kicad_sch'
& $KicadCli sch erc --exit-code-violations -o (Join-Path $packageRoot 'verification\schematic_erc.rpt') $schematicPath
if ($LASTEXITCODE -ne 0) { throw 'ERC failed' }
& $KicadCli sch export netlist --format kicadxml -o (Join-Path $packageRoot 'verification\schematic_netlist.xml') $schematicPath
if ($LASTEXITCODE -ne 0) { throw 'Netlist export failed' }
& $KicadCli sch export svg --exclude-drawing-sheet --draw-hop-over -o (Join-Path $packageRoot 'schematic\render') $schematicPath
if ($LASTEXITCODE -ne 0) { throw 'SVG export failed' }
& $KicadCli sch export pdf --draw-hop-over -o (Join-Path $packageRoot 'schematic\suarez_dac.pdf') $schematicPath
if ($LASTEXITCODE -ne 0) { throw 'PDF export failed' }
