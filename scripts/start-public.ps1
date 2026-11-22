# Chạy backend AURELIA trên máy này và mở ra Internet qua Cloudflare Quick Tunnel (miễn phí, không cần tài khoản).
#   powershell -ExecutionPolicy Bypass -File scripts\start-public.ps1
# Dừng: Ctrl+C trong cửa sổ này (tắt tunnel), rồi đóng cửa sổ API / chạy scripts\stop-public.ps1
#
# Quick Tunnel cấp URL ngẫu nhiên MỚI mỗi lần chạy → sau mỗi lần chạy phải cập nhật VITE_API_BASE trên Vercel và
# Redeploy (xem docs/DEPLOY.md, mục "Phương án miễn phí"). Muốn URL cố định: dùng Named Tunnel với domain riêng.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force $logs | Out-Null
$cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cloudflared) { $cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe" }
if (-not (Test-Path $cloudflared)) { throw "Chưa cài cloudflared: winget install --id Cloudflare.cloudflared" }

Write-Host "1/4 Docker: Postgres + Qdrant"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    for ($i = 0; $i -lt 60; $i++) { Start-Sleep 5; docker info *> $null; if ($LASTEXITCODE -eq 0) { break } }
}
docker start medical-multi-agent-postgres-1 medical-multi-agent-qdrant-1 | Out-Null

Write-Host "2/4 Ollama"
try { Invoke-WebRequest http://127.0.0.1:11434/api/tags -UseBasicParsing -TimeoutSec 5 | Out-Null }
catch { Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden; Start-Sleep 5 }

Write-Host "3/4 API (127.0.0.1:8000 — chỉ tunnel mới truy cập được từ ngoài)"
$api = $null
try { $api = Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing -TimeoutSec 3 } catch { }
if (-not $api) {
    $env:PYTHONIOENCODING = "utf-8"
    Start-Process -FilePath "$root\venv\Scripts\uvicorn.exe" -WindowStyle Minimized `
        -ArgumentList "product.apps.api.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers" `
        -RedirectStandardOutput "$logs\api.log" -RedirectStandardError "$logs\api.err.log"
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep 3
        try { Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing -TimeoutSec 3 | Out-Null; break } catch { }
    }
}
Write-Host "    API sẵn sàng"

Write-Host "4/4 Cloudflare Tunnel"
$tlog = "$logs\tunnel.log"
Remove-Item $tlog -ErrorAction SilentlyContinue
$tunnel = Start-Process -FilePath $cloudflared -PassThru -WindowStyle Hidden `
    -ArgumentList "tunnel --no-autoupdate --url http://127.0.0.1:8000" -RedirectStandardError $tlog
$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) {
    Start-Sleep 2
    if (Test-Path $tlog) { $url = (Select-String -Path $tlog -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1).Matches.Value }
}
if (-not $url) { throw "Không lấy được URL tunnel, xem $tlog" }

Write-Host ""
Write-Host "  URL công khai của API:  $url" -ForegroundColor Green
Write-Host "  Kiểm tra:               $url/health"
Write-Host ""
Write-Host "  Nếu URL khác lần trước: Vercel → Settings → Environment Variables → VITE_API_BASE = $url"
Write-Host "  rồi Deployments → Redeploy. Giữ cửa sổ này mở; Ctrl+C để tắt tunnel."
Set-Content -Path "$logs\public-url.txt" -Value $url
try { Wait-Process -Id $tunnel.Id } finally { Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue }
