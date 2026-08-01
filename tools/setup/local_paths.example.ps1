# ============================================================================
# ARROW — caminhos e identidade DESTA máquina
#
# COPIE este arquivo para `local_paths.ps1` no mesmo diretório e edite.
# `local_paths.*` está no .gitignore: nenhum caminho absoluto de máquina entra
# em arquivo versionado (CLAUDE.md §10).
#
#     Copy-Item tools\setup\local_paths.example.ps1 tools\setup\local_paths.ps1
# ============================================================================

# Nome desta máquina conforme a tabela da §10 do CLAUDE.md.
# Valores válidos: 'PC-Home' | 'PC-Escritorio' | 'Laptop'
#
# NÃO é o hostname do Windows. É a identidade de papel do projeto, e é daqui
# que o Claude Code lê o nome para preencher o campo `Máquina` do STATE.md.
# O hostname não serve: em PC-Home ele é literalmente 'DESKTOP'.
$MachineName = 'PC-Home'

# Pasta MQL5 do terminal. O GUID muda por instalação — confira o seu em:
#     %APPDATA%\MetaQuotes\Terminal\
# Se houver mais de um GUID, o certo é o que contém a subpasta `bases` com o
# nome do seu servidor de broker.
$Mql5Root = "$env:APPDATA\MetaQuotes\Terminal\SEU_GUID_AQUI\MQL5"

# metaeditor64.exe. Também varia por instalação — em PC-Home NÃO está no
# diretório padrão do MetaTrader, e sim numa pasta específica da corretora.
$MetaEditor = 'C:\Program Files\MetaTrader 5\metaeditor64.exe'
