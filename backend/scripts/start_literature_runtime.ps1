$ErrorActionPreference = 'Stop'
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$RuntimeRoot = Join-Path $ProjectRoot '.runtime\literature'
$ManifestPath = Join-Path $RuntimeRoot 'runtime.json'
if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw 'Run backend/scripts/bootstrap_literature_runtime.py first.'
}
$RuntimeManifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$ServerPath = [System.IO.Path]::GetFullPath($RuntimeManifest.server)
$ModelPath = [System.IO.Path]::GetFullPath($RuntimeManifest.model_path)
$AllowedPrefix = [System.IO.Path]::GetFullPath($RuntimeRoot) + [System.IO.Path]::DirectorySeparatorChar
foreach ($TargetPath in @($ServerPath, $ModelPath)) {
    if (-not $TargetPath.StartsWith($AllowedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Runtime paths must remain inside the project runtime directory.'
    }
}
& $ServerPath -m $ModelPath --host 127.0.0.1 --port 8012 -c 4096 -t 4 --parallel 1 --cors-origins localhost --no-cors-credentials --no-webui
