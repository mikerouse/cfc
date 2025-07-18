# Template Testing Script for PowerShell
# Usage: .\test_templates.ps1 [template_name]

param(
    [string]$TemplateName = ""
)

Write-Host ""
Write-Host "🧪 Django Template Syntax Checker" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

if ($TemplateName -eq "") {
    Write-Host "Checking all templates..." -ForegroundColor Yellow
    python check_templates.py
} else {
    Write-Host "Checking template: $TemplateName" -ForegroundColor Yellow
    python check_templates.py $TemplateName
}

Write-Host ""
Read-Host "Press Enter to continue"
