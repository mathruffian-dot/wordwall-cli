# wordwall-cli Agent instructions

本 repo 是可攜式的 Wordwall CLI + Skill。目標是讓 Codex、Claude Code 或其他 Agent
在使用者自己的電腦安裝環境、由使用者本人登入 Wordwall，之後建立活動、指派作業及匯出成績。

## 首次接手

1. 先讀 `README.md`、`INSTALL.md`、`SKILL.md`。
2. 執行 `python wordwall.py doctor --pdf`。
3. 若缺少核心元件，Windows 使用 `.\setup.ps1`；需要 PDF 截圖時加 `-WithPdf`。
4. 若尚未登入，請使用者本人執行 `python wordwall.py login`，再執行
   `python wordwall.py doctor --login --pdf`。

## 安全邊界

- 絕不索取、代填、記錄或提交 Wordwall 帳號密碼。
- session 只存於目前使用者的 `~/.wordwall/state.json`，不得複製到 repo 或分享給他人。
- `debug/` 可能包含帳號畫面；不得 commit。
- 成績含學生資料；預設存於 repo 外，不在終端輸出學生姓名，不得 commit。
- 正式建立活動、建立作業或下載學生成績前，確認使用者已授權該動作與目標。

## 開發與驗證

- Windows 範例一律使用 PowerShell；Mac / Linux 指令另列。
- 核心依賴放 `requirements.txt`；PDF 選用依賴放 `requirements-pdf.txt`。
- 選用功能缺少依賴時，必須提供可直接執行的安裝命令，不得只回傳 import traceback。
- 修改後執行：`python -m py_compile wordwall.py` 及
  `python -m unittest discover -s tests -v`。
- 線上選擇器失敗時，用 `inspect` 與 `debug/` 證據校正，不憑猜測修改。
- Quiz 是已驗證基線；其他 Wordwall 範本只有在實測後才能標示支援。

## 主要入口

- `wordwall.py`：CLI 主程式
- `setup.ps1`：Windows 安裝器
- `requirements-pdf.txt`：PDF 截圖選用依賴
- `SKILL.md`：Agent 使用流程
- `examples/`：內容 JSON 範例
- `tests/`：不寫入 Wordwall 的單元測試
