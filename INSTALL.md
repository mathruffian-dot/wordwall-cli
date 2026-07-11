# wordwall-cli 安裝指南(給其他老師)

每位老師在**自己的電腦**上裝一次。三步驟:①拿到檔案 → ②裝環境 → ③登入你自己的 Wordwall。

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

- **GitHub**(若作者已上傳):`git clone <repo 網址>`
- **直接複製**:把整個 `wordwall-cli` 資料夾用 USB / 雲端硬碟 / zip 複製到你電腦,放哪都行(例如 `C:\wordwall-cli`)。

資料夾裡至少要有:`wordwall.py`、`SKILL.md`、`requirements.txt`、`setup.ps1`、`examples\`。

---

## 步驟 2:一鍵安裝環境

在 PowerShell:

```powershell
cd C:\wordwall-cli
.\setup.ps1
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

---

## 步驟 4(選用):讓 Claude Code 自動辨識這個工具

把整個資料夾放進你的 Claude 技能目錄,Claude Code 就會自動把它當成技能:

```powershell
Copy-Item -Recurse "C:\wordwall-cli" "$env:USERPROFILE\.claude\skills\wordwall"
```

之後在 Claude Code 直接說「用 Wordwall 出一個 quiz」即可。
不搬也行——資料夾留在專案裡,跟 Claude 說「用這個 wordwall-cli 工具建 quiz」,並確認 Claude 知道資料夾路徑。

---

## 目前能做什麼

- ✅ 建立 **Quiz**(選擇題):從題目直接生成真實 Wordwall 活動,回傳連結。
- 🔧 其他範本(配對、分組、轉盤…)、設成學生作業、抓成績:架構已在,選擇器待補。

詳見 `README.md` 與 `SKILL.md`。

---

## Mac / Linux 安裝

沒有 `setup.ps1`,改用:

```bash
cd wordwall-cli
pip install -r requirements.txt
playwright install chromium
python wordwall.py login          # 或 grab-session
python wordwall.py check
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
