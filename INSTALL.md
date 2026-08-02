# wordwall-cli 安裝指南(給其他老師)

每位老師在**自己的電腦**上裝一次。四步驟：①拿到 repo → ②裝環境 → ③登入自己的 Wordwall → ④執行診斷。

> 這是一支 CLI 工具 + 一頁 Skill 說明,不是 MCP server。裝好後,你的 Claude Code 直接用
> 自然語言就能操作(例如「幫我出 8 題光合作用選擇題,做成 Wordwall quiz」)。

---

## 需求

- **Windows + PowerShell**(Mac / Linux 見文末)
- **Python 3.10 以上** — https://www.python.org/downloads/(安裝時**務必勾** _Add python.exe to PATH_)
- **Google Chrome**
- **一個 Wordwall 帳號**(老師帳號免費)

---

## 步驟 1:拿到 `wordwall-cli` 資料夾

擇一即可:

- **GitHub**：`git clone https://github.com/mathruffian-dot/wordwall-cli.git`
- **直接複製**:把整個 `wordwall-cli` 資料夾用 USB / 雲端硬碟 / zip 複製到你電腦,放哪都行(例如 `C:\wordwall-cli`)。

資料夾裡至少要有:`wordwall.py`、`SKILL.md`、`requirements.txt`、`setup.ps1`、`examples\`。

---

## 步驟 2:一鍵安裝環境

在 PowerShell:

```powershell
cd C:\wordwall-cli
.\setup.ps1                 # 只裝 Wordwall 核心功能
.\setup.ps1 -WithPdf        # 同時安裝 PDF 截圖功能
.\setup.ps1 -WithPdf -Login # 安裝後立即開啟本人登入視窗
```

腳本會裝 Playwright、下載 Chromium、並驗證。
若出現「無法載入 setup.ps1,因為執行原則…」,先在同一個視窗跑一次:

```powershell
Set-ExecutionPolicy -Scope Process -Bypass
```

再重跑 `.\setup.ps1`。

> ⚠️ **一機多 Python 的坑**:Windows 常有好幾個 Python。請確定你跑 `setup.ps1` 的
> PowerShell,跟你平常開 Claude Code 用的是**同一個** `python`(在 PowerShell 打
> `(Get-Command python).Source` 可查)。裝在不同的 python,工具會說「找不到 Playwright」。

---

## 步驟 3:登入你自己的 Wordwall(每人各自登)

登入狀態存在**你自己電腦**的 `C:\Users\<你>\.wordwall\state.json`,**不能共用別人的**。

### 方式 A(最簡單):Email + 密碼

```powershell
python wordwall.py login
```

在跳出的視窗用 **Email + 密碼**登入,**不要點 Sign in with Google**(Google 會封鎖自動化瀏覽器)。
只有 Google 帳號、沒設過密碼?→ 在登入頁點「Forgot password」用信箱設一組密碼。

### 方式 B:借用真實 Chrome 的登入(想繼續用 Google 就走這條)

```powershell
# 1) 完全關閉 Chrome,再用除錯埠重開(近版 Chrome 一定要加 --user-data-dir)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\ww-debug"
# 2) 在跳出的乾淨 Chrome 視窗登入 wordwall.net(Google 或 Email 都行)
# 3) 回 PowerShell 執行:
python wordwall.py grab-session
```

### 驗證登入

```powershell
python wordwall.py check
```

出現 `[OK] 登入有效` 就完成了。

### 完整診斷

```powershell
python wordwall.py doctor --login --pdf
```

`doctor` 會檢查 Python 版本、Playwright、Chromium、目前使用者的登入狀態與 PDF 截圖元件。
若缺少任何元件，會直接顯示安裝命令。Agent 應把命令交給使用者執行，不可要求帳號密碼。

---

## 步驟 4(選用):讓 Codex / Claude Code 自動辨識這個工具

把整個資料夾放進 Agent 的技能目錄，或讓 Agent 直接讀取 repo 內的 `SKILL.md`。
Claude Code 範例：

```powershell
Copy-Item -Recurse "C:\wordwall-cli" "$env:USERPROFILE\.claude\skills\wordwall"
```

Codex 範例：

```powershell
Copy-Item -Recurse "C:\wordwall-cli" "$env:USERPROFILE\.codex\skills\wordwall"
```

之後在 Claude Code 直接說「用 Wordwall 出一個 quiz」即可。
不搬也行——資料夾留在專案裡,跟 Claude 說「用這個 wordwall-cli 工具建 quiz」,並確認 Claude 知道資料夾路徑。

---

## PDF 截圖題（選用）

若 `doctor --pdf` 顯示缺少元件：

```powershell
python -m pip install -r requirements-pdf.txt
```

整頁輸出：

```powershell
python wordwall.py pdf-screenshot --input "C:\題本.pdf" --page 2 --output "C:\題圖\page2.png"
```

指定區域裁切：

```powershell
python wordwall.py pdf-screenshot --input "C:\題本.pdf" --page 2 `
  --crop "55,75,540,215" --output "C:\題圖\q01.png"
```

座標單位是 PDF 點。先輸出整頁再決定裁切範圍；上傳前要目視確認題幹、選項、幾何圖完整。

---

## 目前能做什麼

- ✅ 建立文字或圖片 Quiz 與配對活動。
- ✅ 建立 Group sort、Speed sorting、Speaking cards、簡易轉盤及句子填空。
- ✅ 建立 True or false、Open the box、Rank order、Matching pairs 與 Labelled diagram。
- ✅ PDF 整頁／區域截圖，缺少元件時提供安裝指令。
- ✅ 建立學生作業並取得 `/play/` 連結。
- ✅ My Results 清單與 Excel／CSV 實際下載。
- 🔧 True or false、問答轉盤、Crossword、標示圖等範本待後續實測。
- 🔧 問答轉盤／問答盒、Crossword 等尚未標示支援的範本待後續實測。

常用指令:

```powershell
python wordwall.py plan --request "圖片配圖片的幾何配對遊戲"
python wordwall.py recommend --intent "圖片配對" --implemented-only
python wordwall.py create --content examples\image_quiz_example.json --dry-run
python wordwall.py create --content examples\group_sort_example.json --editor-check --headless
python wordwall.py assign --activity-url "https://wordwall.net/resource/123456" --title "幾何練習" --dry-run --headless
python wordwall.py results list --title "幾何練習" --headless
```

建立流程固定為 `recommend` → `--dry-run` → `--editor-check` → 使用者確認 → 正式建立。
成績檔不得放進 GitHub repo。

詳見 `README.md` 與 `SKILL.md`。

---

## Mac / Linux 安裝

沒有 `setup.ps1`,改用:

```bash
cd wordwall-cli
pip install -r requirements.txt
python -m playwright install chromium
python -m pip install -r requirements-pdf.txt  # 需要 PDF 截圖時才裝
python wordwall.py login          # 或 grab-session
python wordwall.py doctor --login --pdf
```

除錯 Chrome 指令的路徑改成你系統的 Chrome(Mac 例:
`/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/ww-debug`)。

---

## 常見問題

| 症狀 | 解法 |
|---|---|
| `找不到 python` | 裝 Python 並勾 Add to PATH,重開 PowerShell |
| `尚未安裝 Playwright`(明明裝過) | 裝到別的 python 了;用 `(Get-Command python).Source` 對齊,再重跑 `setup.ps1` |
| Google 登入頁說「這個瀏覽器可能有安全疑慮」 | 正常,Google 擋自動化;改用方式 A(Email)或方式 B(grab-session) |
| `除錯埠 9222 連不上` | Chrome 沒完全關就重開、或忘了加 `--user-data-dir`;關乾淨再重開 |
| 建活動時選擇器對不上 | Wordwall 改版了;跑 `python wordwall.py inspect --url https://wordwall.net/create` 重新校正 |
| `PDF 截圖元件` 缺少 | 執行 `python -m pip install -r requirements-pdf.txt`，或 Windows 執行 `.\setup.ps1 -WithPdf` |
| `doctor` 顯示尚未登入 | 執行 `python wordwall.py login`，由使用者本人在瀏覽器登入 |
