# 台灣股市三大法人籌碼爬蟲 (TWSE & TPEx Institutional Investors Scraper)

這是一個專為台灣股市設計的 Python 爬蟲腳本，旨在自動化下載、整理並儲存上市(TWSE)與上櫃(TPEx)市場每日的三大法人（外資、投信、自營商）買賣超資料。

程式會根據您的客製化規則，精準地篩選並命名欄位，並將最終成果結構化地存檔，方便您進行後續的資料分析與策略研究。

## ✨ 主要功能

* **雙市場支援**: 同時爬取台灣證券交易所 (TWSE) 與證券櫃檯買賣中心 (TPEx) 的資料。
* **三大法人完整資料**: 根據最新規則，精準擷取外資、投信、自營商的買賣超數據。
* **本地清單驅動**: 透過 `stock_list.csv` 檔案，輕鬆管理您想追蹤的股票清單。
* **歷史資料抓取**: 支援指令列參數，可一次性下載過去 N 天的歷史資料。
* **增量自動更新**: 再次執行時，程式會自動跳過已下載的日期，只抓取遺漏的資料。
* **並行下載**: 採用多執行緒技術，大幅加速資料下載過程。
* **結構化存檔**: 將每日資料與歷史累加資料，依據市場別 (`twse_raw`, `tpex_raw`) 和股票代號，分門別類地儲存。

## 🌐 資料來源 (Data Sources)

本程式的資料來源均為台灣證券主管機關的公開資訊。程式透過模擬瀏覽器行為，直接存取其後端資料API。

### 上市 (TWSE) - 台灣證券交易所

* **使用者介面:**
    * 外資: `https://www.twse.com.tw/zh/trading/foreign/twt38u.html`
    * 投信: `https://www.twse.com.tw/zh/trading/foreign/twt44u.html`
    * 自營商: `https://www.twse.com.tw/zh/trading/foreign/twt43u.html`
* **實際資料API (CSV下載連結範本):**
    * 外資: `https://www.twse.com.tw/rwd/zh/fund/TWT38U?date=YYYYMMDD&response=csv`
    * 投信: `https://www.twse.com.tw/rwd/zh/fund/TWT44U?date=YYYYMMDD&response=csv`
    * 自營商: `https://www.twse.com.tw/rwd/zh/fund/TWT43U?date=YYYYMMDD&response=csv`
    * > `YYYYMMDD` 會由程式動態替換為目標日期，例如 `20250919`。

### 上櫃 (TPEx) - 證券櫃檯買賣中心

* **使用者介面:**
    * 三大法人: `https://www.tpex.org.tw/zh-tw/mainboard/trading/major-institutional/detail/day.html`
* **實際資料API (CSV下載連結範本):**
    * 三大法人: `https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&d=YYY/MM/DD&t=D&o=csv`
    * > `YYY/MM/DD` 會由程式動態替換為目標日期的民國年格式，例如 `114/09/19`。

## 🚀 環境設定與使用教學 (Step-by-Step Guide)

請依照以下步驟設定您的環境並執行程式。

### 步驟一：準備環境

1.  **安裝 Python**: 請確認您的電腦已安裝 Python 3.8 或更高版本。
2.  **建立專案資料夾**: 在您喜歡的位置，建立一個新的資料夾來存放專案檔案（例如 `my_scraper`）。
3.  **安裝必要函式庫**: 打開您的終端機（在Windows上是 `cmd` 或 `PowerShell`），執行以下指令來安裝程式所需的 `pandas` 和 `requests` 函式庫：
    ```bash
    pip install pandas requests
    ```

### 步驟二：建立核心檔案

1.  **建立主程式檔案**: 在您剛剛建立的專案資料夾中，新增一個名為 `twse_scraper.py` 的檔案。將我們之前確認過的最終版Python程式碼完整地貼入此檔案中。

2.  **建立股票清單檔案**: 在同一個資料夾中，新增一個名為 `stock_list.csv` 的空白檔案。

### 步驟三：設定您的股票清單

1.  用文字編輯器或Excel打開 `stock_list.csv` 檔案。
2.  請務必**包含標頭行 (Header)**，標頭的名稱必須是 `stock_code`, `stock_name`, `上市上櫃`。程式會自動在檔案中尋找這一行，所以它不一定要在第一行。
3.  在標頭行下方，每一行新增一筆您想追蹤的股票資料。
    * `stock_code`: 股票代號
    * `stock_name`: 股票名稱（此欄位僅供您自己參考，程式不會使用）
    * `上市上櫃`: 請填寫 `上市` 或 `上櫃`

**格式範例:**
```csv
stock_code,stock_name,上市上櫃
2330,台積電,上市
8069,元太,上櫃
6488,環球晶,上櫃
0050,元大台灣50,上市
```

### 步驟四：執行爬蟲程式

1.  **打開終端機**: 開啟您的終端機或命令提示字元。
2.  **切換目錄**: 使用 `cd` 指令，切換到您存放專案的資料夾。例如：
    ```bash
    cd "F:\Vibe Coding\twse_scraper"
    ```
3.  **執行指令**:
    * **每日更新 (抓取當日最新資料)**:
        這是在設定完成後，每天例行執行抓取最新資料的指令。
        ```bash
        python twse_scraper.py
        ```

    * **抓取歷史資料 (首次執行推薦)**:
        這個指令會從今天往前抓取您指定的天數。例如，要抓取最近60天的資料：
        ```bash
        python twse_scraper.py --days 60
        ```
        您可以將 `60` 替換成任何您需要的天數。

### 步驟五：檢查輸出結果

程式執行完畢後，您會在專案資料夾底下看到一個新建的 `data` 資料夾，裡面包含了所有抓取下來的資料。

* `data/twse_raw/`: 存放所有「上市」公司的資料。
* `data/tpex_raw/`: 存放所有「上櫃」公司的資料。

在每個公司的股號資料夾內：
* **每日檔案 (`YYYY-MM-DD.csv`)**: 是該股票當天的三大法人買賣超詳細欄位。
* **累加檔案 (`{股號}.csv`)**: 是該股票截至目前為止，所有已下載日期的歷史資料彙總。