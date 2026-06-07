# Open-Paxel installer (Windows)
$ErrorActionPreference = "Stop"

Write-Host "Open-Paxel installer"
Write-Host "===================="

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is required. Install it:"
    Write-Host "  powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
    exit 1
}

Set-Location $PSScriptRoot

Write-Host "Creating .venv and installing dependencies with uv..."
uv sync --all-groups

Write-Host ""
Write-Host "Installed open-paxel CLI into .venv"
Write-Host ""
Write-Host "Activate the environment:"
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Or run commands via uv:"
Write-Host "  uv run open-paxel discover"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. uv run open-paxel init-config"
Write-Host "  2. uv run open-paxel discover"
Write-Host "  3. uv run open-paxel upload -y"
Write-Host "  4. uv run open-paxel profile --open"
