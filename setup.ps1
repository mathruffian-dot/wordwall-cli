# wordwall-cli 一鍵安裝(Windows / PowerShell)
# 用法: .\setup.ps1 [-WithPdf] [-Login]
# 若被安全性擋住,先在同一個視窗跑:  Set-ExecutionPolicy -Scope Process -Bypass

[CmdletBinding()]
param(
    [switch]$WithPdf,
    [switch]$Login
)

$ErrorActionPreference = 'Stop'

Write-Host "===== wordwall-cli 安裝開始 =====" -ForegroundColor Cyan

# 1. 找 python(要跟你的 Claude Code / 終端機用的是同一個)
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Host "找不到 python。請先安裝 Python 3.10 以上:" -ForegroundColor Red
    Write-Host "  https://www.python.org/downloads/  (安裝時務必勾選 Add python.exe to PATH)" -ForegroundColor Red
    exit 1
}
Write-Host ("使用 python: " + $pyCmd.Source)
& $pyCmd.Source --version
& $pyCmd.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 版本過舊。請安裝 Python 3.10 以上。" -ForegroundColor Red
    exit 1
}

# 2. 安裝 Playwright 套件(裝進上面這個 python)
Write-Host "`n[1/3] 安裝 Playwright 套件..." -ForegroundColor Cyan
& $pyCmd.Source -m pip install -r "$PSScriptRoot\requirements.txt"
if ($LASTEXITCODE -ne 0) { Write-Host "pip 安裝失敗,請看上方錯誤訊息。" -ForegroundColor Red; exit 1 }

# 3. 下載 Chromium 瀏覽器核心
Write-Host "`n[2/3] 下載 Chromium 瀏覽器核心(約 170MB,請稍候)..." -ForegroundColor Cyan
& $pyCmd.Source -m playwright install chromium
if ($LASTEXITCODE -ne 0) { Write-Host "Chromium 下載失敗,請確認網路後重跑。" -ForegroundColor Red; exit 1 }

# 4. 驗證
Write-Host "`n[3/3] 驗證 Chromium 能否啟動..." -ForegroundColor Cyan
& $pyCmd.Source -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); b.close(); p.stop(); print('Chromium 啟動成功')"
if ($LASTEXITCODE -ne 0) { Write-Host "Chromium 啟動驗證失敗。" -ForegroundColor Red; exit 1 }

if ($WithPdf) {
    Write-Host "`n[選用] 安裝 PDF 截圖元件..." -ForegroundColor Cyan
    & $pyCmd.Source -m pip install -r "$PSScriptRoot\requirements-pdf.txt"
    if ($LASTEXITCODE -ne 0) { Write-Host "PDF 元件安裝失敗。" -ForegroundColor Red; exit 1 }
}

$doctorArgs = @("$PSScriptRoot\wordwall.py", "doctor")
if ($WithPdf) { $doctorArgs += "--pdf" }
& $pyCmd.Source @doctorArgs
if ($LASTEXITCODE -ne 0) { Write-Host "環境診斷未通過，請依上方建議處理。" -ForegroundColor Red; exit 1 }

Write-Host "`n===== 環境安裝完成 =====" -ForegroundColor Green
Write-Host "下一步:登入你自己的 Wordwall 帳號(每位老師各自登一次)"
Write-Host "  最快:  python wordwall.py login   然後用『Email + 密碼』登入(不要點 Sign in with Google)"
Write-Host "  完成後:python wordwall.py check    出現 [OK] 就代表可以用了"
Write-Host "  只有 Google 帳號、被 Google 擋?→ 改用 grab-session,步驟見 INSTALL.md"
Write-Host "  需要 PDF 截圖?→ .\setup.ps1 -WithPdf"

if ($Login) {
    Write-Host "`n即將開啟瀏覽器，請登入你自己的 Wordwall 帳號。" -ForegroundColor Cyan
    & $pyCmd.Source "$PSScriptRoot\wordwall.py" login
}
