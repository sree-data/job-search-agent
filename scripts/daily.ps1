# Runs the daily job-search agent pass in headless mode on Windows.
# Schedule with Task Scheduler: Program = powershell.exe, Arguments = -File "C:\path\to\job-search-agent\scripts\daily.ps1"
Set-Location (Join-Path $PSScriptRoot "..")
"=== $(Get-Date) ===" | Tee-Object -FilePath "pipeline\daily.log" -Append
claude -p "/daily" --output-format text | Tee-Object -FilePath "pipeline\daily.log" -Append
