# Tắt tunnel và API do scripts\start-public.ps1 khởi động (không tắt Docker / Ollama).
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process
Get-CimInstance Win32_Process -Filter "Name = 'uvicorn.exe' OR Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like "*product.apps.api.main:app*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
Write-Host "Đã tắt tunnel và API."
