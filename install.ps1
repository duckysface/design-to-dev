# design-to-dev — installation Windows sans npm ni clone.
#   irm https://raw.githubusercontent.com/duckysface/design-to-dev/main/install.ps1 | iex
#   $env:DESIGN_TO_DEV_AGENTS = "codex"; irm .../install.ps1 | iex     (claude, codex ou all ; défaut : all)
# Avec Node 18+, délègue à bin/cli.js ; sinon copie la skill directement.
$ErrorActionPreference = "Stop"

$Repo = "duckysface/design-to-dev"
$Ref = if ($env:DESIGN_TO_DEV_REF) { $env:DESIGN_TO_DEV_REF } else { "main" }
$Name = "design-to-dev"
$Choice = if ($env:DESIGN_TO_DEV_AGENTS) { $env:DESIGN_TO_DEV_AGENTS.ToLower() } else { "all" }
$Agents = switch ($Choice) {
    "claude" { @("claude") }
    "codex" { @("codex") }
    "all" { @("claude", "codex") }
    default { throw "DESIGN_TO_DEV_AGENTS doit valoir claude, codex ou all (reçu : $Choice)" }
}

$Tmp = Join-Path ([IO.Path]::GetTempPath()) "design-to-dev-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $Tmp | Out-Null
try {
    Write-Host "Téléchargement de $Repo ($Ref)…"
    $Zip = Join-Path $Tmp "src.zip"
    Invoke-WebRequest -UseBasicParsing "https://codeload.github.com/$Repo/zip/refs/heads/$Ref" -OutFile $Zip
    Expand-Archive -Path $Zip -DestinationPath $Tmp
    $Src = Join-Path $Tmp "$Name-$Ref"
    if (-not (Test-Path (Join-Path $Src "SKILL.md"))) { throw "Archive inattendue : SKILL.md introuvable." }

    $Node = Get-Command node -ErrorAction SilentlyContinue
    if ($Node -and [int]((& node -p "process.versions.node").Split(".")[0]) -ge 18) {
        $Flags = $Agents | ForEach-Object { "--$_" }
        & node (Join-Path $Src "bin/cli.js") install -y @Flags
        return  # pas d'exit : via iex, il fermerait la fenêtre PowerShell de l'utilisateur
    }

    foreach ($Agent in $Agents) {
        $Base = if ($Agent -eq "claude") {
            if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME ".claude" }
        } else { Join-Path $HOME ".agents" }
        $Dst = Join-Path (Join-Path $Base "skills") $Name
        $Skill = Join-Path $Dst "SKILL.md"
        if ((Test-Path $Dst) -and -not ((Test-Path $Skill) -and (Select-String -Path $Skill -Pattern "^name:\s*$Name\s*$" -Quiet))) {
            Write-Warning "$Dst existe et ne contient pas $Name : ignoré."
            continue
        }
        $Stage = "$Dst.tmp"
        if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
        New-Item -ItemType Directory -Force -Path $Stage | Out-Null
        foreach ($Item in "SKILL.md", "LICENSE", "README.md", "scripts", "references", "templates") {
            $P = Join-Path $Src $Item
            if (Test-Path $P) { Copy-Item -Recurse -Path $P -Destination $Stage }
        }
        Get-ChildItem -Path $Stage -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
        Set-Content -Path (Join-Path $Stage ".version") -Value $Ref
        if (Test-Path $Dst) { Remove-Item -Recurse -Force $Dst }
        Move-Item -Path $Stage -Destination $Dst
        Write-Host "  ✓ $Agent : $Dst"
    }
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Warning "Python 3.9+ introuvable : l'installer avant d'utiliser la skill."
    }
    Write-Host 'Redémarrer l''agent. Claude Code : /design-to-dev <dossier> — Codex : $design-to-dev <dossier>'
}
finally {
    Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue
}
