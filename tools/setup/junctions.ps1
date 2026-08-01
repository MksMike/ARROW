# ============================================================================
# ARROW — criação das junctions entre o terminal MT5 e o repositório
#
# O repositório é a fonte de verdade. A pasta MQL5 do terminal aponta para
# dentro dele (CLAUDE.md §10). Este script é idempotente: rodar duas vezes
# não quebra nada.
#
#     pwsh -File tools\setup\junctions.ps1
#     pwsh -File tools\setup\junctions.ps1 -WhatIf   # só mostra o que faria
#
# Junction de diretório não exige privilégio de administrador no Windows —
# ao contrário de symlink. É por isso que usamos junction.
# ============================================================================

[CmdletBinding(SupportsShouldProcess = $true)]
param()

$ErrorActionPreference = 'Stop'

$RepoRoot   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LocalPaths = Join-Path $PSScriptRoot 'local_paths.ps1'

if (-not (Test-Path $LocalPaths)) {
    Write-Error @"
Falta o arquivo tools\setup\local_paths.ps1.

Ele guarda os caminhos e a identidade desta máquina, e não é versionado.
Crie a partir do exemplo:

    Copy-Item tools\setup\local_paths.example.ps1 tools\setup\local_paths.ps1

e edite com o GUID do seu terminal.
"@
}

. $LocalPaths

foreach ($v in @('MachineName', 'Mql5Root', 'MetaEditor')) {
    if (-not (Get-Variable -Name $v -Scope Script -ErrorAction SilentlyContinue) -and
        -not (Get-Variable -Name $v -ErrorAction SilentlyContinue)) {
        Write-Error "local_paths.ps1 não define `$$v."
    }
}

if (-not (Test-Path $Mql5Root)) {
    Write-Error "Mql5Root não existe: $Mql5Root`nConfira o GUID em %APPDATA%\MetaQuotes\Terminal\"
}

Write-Host "Maquina    : $MachineName"
Write-Host "Repo       : $RepoRoot"
Write-Host "MQL5 root  : $Mql5Root"
Write-Host ''

# nome da junction dentro do terminal  ->  destino dentro do repositório
$Links = [ordered]@{
    'Include\ARROW'    = 'MQL5\Include\ARROW'
    'Indicators\ARROW' = 'MQL5\Indicators\ARROW'
    'Experts\ARROW'    = 'MQL5\Experts\ARROW'
    'Scripts\ARROW'    = 'MQL5\Scripts\ARROW'
}

$failed = 0

foreach ($entry in $Links.GetEnumerator()) {
    $linkPath   = Join-Path $Mql5Root $entry.Key
    $targetPath = Join-Path $RepoRoot $entry.Value

    if (-not (Test-Path $targetPath)) {
        Write-Warning "destino nao existe no repo, pulando: $targetPath"
        $failed++
        continue
    }

    $existing = Get-Item -LiteralPath $linkPath -Force -ErrorAction SilentlyContinue

    if ($null -ne $existing) {
        # Já existe. Só três desfechos são aceitáveis: é a junction certa
        # (nada a fazer), é a junction errada (refaz), ou é diretório real
        # com conteúdo (para — apagar seria destruir trabalho).
        if ($existing.LinkType -eq 'Junction') {
            $current = @($existing.Target)[0]
            if ($current -and ($current.TrimEnd('\') -ieq $targetPath.TrimEnd('\'))) {
                Write-Host "ok    $($entry.Key)  ->  ja aponta para o repo"
                continue
            }
            Write-Host "refaz $($entry.Key)  (apontava para $current)"
            if ($PSCmdlet.ShouldProcess($linkPath, 'remover junction antiga')) {
                [System.IO.Directory]::Delete($linkPath, $false)
            }
        }
        else {
            $count = @(Get-ChildItem -LiteralPath $linkPath -Force -ErrorAction SilentlyContinue).Count
            Write-Warning @"
$linkPath e um diretorio real com $count item(ns), nao uma junction.
Nao vou apagar. Mova ou remova manualmente e rode de novo.
"@
            $failed++
            continue
        }
    }

    if ($PSCmdlet.ShouldProcess($linkPath, "junction -> $targetPath")) {
        New-Item -ItemType Junction -Path $linkPath -Target $targetPath | Out-Null
        Write-Host "cria  $($entry.Key)  ->  $targetPath"
    }
}

Write-Host ''
if (-not (Test-Path $MetaEditor)) {
    Write-Warning "metaeditor64.exe nao encontrado em: $MetaEditor`nCompilacao por linha de comando nao vai funcionar ate corrigir local_paths.ps1."
    $failed++
}
else {
    Write-Host "metaeditor : $MetaEditor"
}

if ($failed -gt 0) {
    Write-Host ''
    Write-Warning "$failed problema(s) acima. Nada foi declarado pronto."
    exit 1
}

Write-Host 'Junctions ok.'
