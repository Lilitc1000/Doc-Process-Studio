---
name: project-architecture-docx
description: Generate a project-specific system architecture and design DOCX by reading the current folder, analyzing the codebase, and writing a document that follows the provided reference document's cover, typography, table style, and overall layout as closely as possible with python-docx. Use when the user asks Codex to read an existing project and output a professional architecture/design document, technical design document, implementation design document, or similar DOCX based on repository contents, especially when a reference DOCX format must be followed and version/date defaults are required.
---

# Project Architecture Docx

## 概覽

根據當前專案目錄內容，自動生成一份技術文檔類型的 `.docx` 文件。文檔標題默認為「系統架構與設計文檔」，但可按使用者要求切換為部署文檔、運維手冊、測試報告、設計說明書等其它標題。優先復用 `assets/reference-template.docx` 的版式、字體、標題樣式和表格觀感，並使用 `python-docx` 產生最終文檔。

## 工作流程

1. 先閱讀目前專案，而不是直接寫文檔。
2. 優先識別系統名稱、主要技術棧、部署方式、資料存儲、模組邊界、測試與 CI/CD。
3. 如果使用者沒有提供版本號，預設為 `1.0`。
4. 如果使用者沒有提供日期，使用當前日期。
5. 先確認使用者是否已明確指定「系統名稱」和「文檔標題」：
   - 若使用者像「請幫我寫一份 XX 的 XX」這樣明確給出，則前一個 `XX` 視為系統名稱，後一個 `XX` 視為文檔標題，直接採用，不要再自行切詞或重猜。
   - 若使用者沒有明確給出，但提供了 Markdown 或其它源文檔，應由你先讀該源文檔標題，並在模型層理解出系統名稱與文檔標題，再把結果顯式傳給腳本。
   - 若仍無法判斷，文檔標題默認回退為「系統架構與設計文檔」，系統名稱再根據專案本身推斷。
6. 先確認使用者是否已指定文檔章節結構：
   - 若使用者明確提供「有多少章、每章標題、每章/每節正文內容」，則優先按使用者提供的結構生成。
   - 若使用者只提供部分章節或只有標題，也應由你在模型層補足正文內容，再交給腳本。
   - 不要依賴腳本自動生成章節或正文；腳本只負責把已整理好的文檔結構排版成 docx。
7. 先把你整理好的完整章節與正文寫成 `doc-plan`。
8. 使用 `scripts/generate_architecture_doc.py` 生成 `.docx`。
9. 生成後自行檢查輸出文件名、章節標題、表格內容是否與專案相符。
10. 無論輸入來源是使用者提供的 Markdown、JSON/YAML 章節規劃，還是你在模型層補出的內容，最終寫入 Word 的正文、標題、表格文字都必須統一為繁體中文。

## 專案閱讀要求

優先用快速方式建立上下文：

- 使用 `rg --files` 取得檔案清單。
- 重點查看 `README*`、`package.json`、`pyproject.toml`、`requirements*.txt`、`Dockerfile*`、`docker-compose*`、`.github/workflows/*`、`__manifest__.py`、`pom.xml`、`Cargo.toml`、`go.mod`、`Makefile`。
- 忽略大型產物與依賴目錄，例如 `node_modules`、`.git`、`dist`、`build`、`.venv`、`coverage`、`__pycache__`。

如果專案很大，先抓骨架與關鍵設定，再決定是否補讀核心模組。不要把沒有證據的功能、架構或部署方式寫進文檔。

## 生成命令

常用命令：

```bash
python3 scripts/generate_architecture_doc.py \
  --project-root . \
  --document-title "系統架構與設計文檔" \
  --output "./系統架構與設計文檔-V1.0.docx"
```

如果使用者提供系統名稱或版本號，顯式帶入：

```bash
python3 scripts/generate_architecture_doc.py \
  --project-root . \
  --system-name "XXX 系統" \
  --document-title "詳細設計說明書" \
  --version "2.3" \
  --output "./XXX系統架構與設計文檔-V2.3.docx"
```

如果需要從 skill 目錄外直接執行，使用：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/project-architecture-docx/scripts/generate_architecture_doc.py" \
  --project-root . \
  --document-title "系統架構與設計文檔" \
  --output "./系統架構與設計文檔-V1.0.docx"
```

如果需要顯式控制刷新行為，可用：

```bash
python3 scripts/generate_architecture_doc.py \
  --project-root . \
  --refresh-with-word \
  --output "./系統架構與設計文檔-V1.0.docx"
```

或：

```bash
python3 scripts/generate_architecture_doc.py \
  --project-root . \
  --no-refresh-with-word \
  --output "./系統架構與設計文檔-V1.0.docx"
```

注意：

- 正常正式生成時，不要主動加 `--no-refresh-with-word`，除非只是做版式或正文測試。
- 腳本執行完成後會輸出「刷新後端」與「自動刷新」狀態，用來判斷這次是否真的調用了 Word/本機文檔引擎刷新。

如果使用者已提供章節規劃，可先整理成 JSON 或 YAML，再帶入：

```bash
python3 scripts/generate_architecture_doc.py \
  --project-root . \
  --doc-plan ./doc-plan.yaml \
  --output "./系統架構與設計文檔-V1.0.docx"
```

## 輸出約定

- 封面頁：系統名稱替換為專案名稱；版本未提供時用 `1.0`；日期使用當前日期。
- 封面與頁眉標題：優先使用使用者明確指定的文檔標題；若未指定，則由你在模型層判斷或回退到默認標題。
- 修訂歷史：至少生成一筆初稿記錄。
- 目錄頁：插入 Word TOC 欄位；腳本會自動探測當前環境是否具備可用的刷新能力。若在 WSL + Windows Word 或原生 Windows + Word 環境中，會默認在生成後自動打開 Word 更新目錄、頁碼與日期域；若環境不支持，則保留可更新的欄位並降級輸出。
- 正文：章節標題與內容由你在模型層先整理好，再交給腳本渲染；不要期待腳本自行補標題或正文。
- 所有輸出內容必須統一為繁體中文；若來源是簡體中文，需在生成前或寫入時完成轉換。
- 內容必須來自專案事實；推斷內容要明確收斂，避免編造。

## 模板與參考

- 版式模板：`assets/reference-template.docx`
- 封面 Logo：`assets/logo.png`
- 版式觀察摘要：`references/reference-format.md`
- 繁簡轉換：優先使用成熟的 `OpenCC` 後端，不允許用硬編碼詞表或手寫字典替代

優先策略：

1. 優先使用 `reference-template.docx` 作為 `python-docx` 的載入模板。
2. 清空正文後重建內容，保留模板中的樣式、主題與節配置。
3. 預設使用 `assets/logo.png` 作為封面 Logo；如需更換 Logo，直接替換該文件，不要修改腳本中的圖像邏輯。
4. 僅在模板缺失時退回腳本中的 A4、字體、標題和表格樣式預設。

## 腳本說明

主腳本：

- `scripts/generate_architecture_doc.py`
- `scripts/refresh_with_word.py`
- `scripts/refresh_with_word.ps1`

它會：

- 掃描專案根目錄與常見設定文件。
- 解析常見生態的基本資訊，例如 Python、Node.js、Docker Compose、Odoo 模組等。
- 把你已整理好的 `doc-plan` 章節、正文與表格內容排版進 Word。
- 用 `python-docx` 產出接近參考文檔觀感的 `.docx`。
- 默認自動探測是否可刷新文檔域；若當前環境支持，會自動更新目錄、頁碼和日期域後再保存。
- 目前已支持：
  - WSL + Windows Word
  - 原生 Windows + Word
- 若在普通 Linux 環境中沒有可用的 Word 刷新能力，腳本會自動跳過該步驟，不會報錯中斷。
- `--doc-plan` 是正文生成的主入口；正常使用時應始終由你先生成完整 `doc-plan` 再調腳本。
- 繁體中文轉換必須使用成熟後端：
  - 優先使用當前 Python 環境可導入的 `OpenCC`
  - 或系統已安裝的 `opencc` 命令列工具
  - 在 WSL/Windows 混合環境下，可回退到 Windows Python 中安裝的 `opencc-python-reimplemented`
  - 若以上後端均不可用，應明確報錯，不要改用手寫映射繼續生成

## 使用此 skill 時的行為要求

- 在真正生成前，先簡短告知你將檢查哪些專案資訊。
- 如果使用者沒有明確指定章節結構，應先詢問或確認是否沿用參考文檔式的預設章節；若使用者未提出特別要求，可直接使用預設章節。
- 如果使用者明確指定了系統名稱和文檔標題，必須直接採用；不要再根據字面特徵替使用者重猜。
- 只有在使用者沒有明確給出系統名稱或文檔標題時，才允許由你在模型層從 Markdown/源文檔標題中推斷；不要把這類語義推斷寫進腳本。
- 如果使用者已明確指定章節數、標題或正文，應優先遵從，不要再把固定章節硬套進去。
- 即使使用者沒有提供正文，也應由你在模型層根據專案、文檔、提示詞或使用者要求來補全文字；不要依賴腳本輸出固定正文。
- 如果使用者提供的是簡體中文 Markdown 或簡體章節內容，生成前需要先轉為繁體中文，再交給腳本或寫入文檔。
- 生成後，回報輸出路徑、推斷出的系統名稱、版本、主要技術棧。
- 如果專案資訊不足以支撐某一章節，不要捏造；可以寫成「目前從代碼庫未發現明確證據」並給出保守說明。
- 如果使用者提供了自己的參考文檔，優先改用使用者提供的參考文檔，並保留目前 skill 的腳本作為生成骨架。
