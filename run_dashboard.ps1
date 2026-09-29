# Launch the Streamlit dashboard with the project's virtual environment (.venv)
# Lanza el dashboard de Streamlit con el entorno virtual del proyecto (.venv)
#   Usage / Uso:  .\run_dashboard.ps1
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "No .venv found. Create it first / Primero crea el entorno:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements-dev.txt"
    exit 1
}
Set-Location $PSScriptRoot
& $venvPython -m streamlit run app/dashboard.py @args
