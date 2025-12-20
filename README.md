# taiwan-stock-monitor
自動化台股全方位監控系統：每日產出 9 張（週/月/年 × 高/收/低）10% 分箱報酬分析圖表，並透過 Resend API 發送互動式電子郵件報表。  Automated Taiwan Stock Monitor: Generates 9 comprehensive charts (Week/Month/Year × High/Close/Low) with 10% bin return analysis, delivering interactive daily email reports via Resend API.

# 🇹🇼 Taiwan Stock Multi-Matrix Monitor | 台股全方位矩陣監控系統

[English](#english) | [中文](#中文)

---

## English

### 🚀 Project Overview
A fully automated Taiwan stock market monitoring system that performs multi-threaded data scraping, statistical matrix analysis, and professional reporting. The system visualizes market breadth and momentum through a 3x3 distribution matrix (Week/Month/Year K-line vs. High/Close/Low price).

### 🛠️ Key Features
- **Auto-Scraping**: Automatically fetches all listed/OTC/ETF/Innovation Board tickers from TWSE.
- **Data Pipeline**: Multi-threaded historical data downloading via `yfinance`.
- **Matrix Analysis**: Generates 9 distinct distribution charts showing market health.
- **Smart Reporting**: Sends professional HTML emails via **Resend API**, featuring color-coded tables and direct links to **WantGoo Technical Charts**.
- **GitHub Actions**: 100% serverless, scheduled execution (CST 13:30/14:00).

### 🧰 Tech Stack
- **Language**: Python 3.10
- **Libraries**: Pandas, Matplotlib, Requests, Concurrent.futures, Tqdm
- **Automation**: GitHub Actions
- **Infrastructure**: Ubuntu-latest (with CJK Font support)

---

## 中文

### 🚀 專案概述
一個完全自動化的台股監控系統，執行多執行緒數據爬取、矩陣統計分析並寄送專業報表。系統透過 3x3 分佈矩陣（週/月/年K 結合 最高/收盤/最低價）視覺化呈現市場漲跌家數與進攻力道。

### 🛠️ 核心功能
- **自動爬蟲**：自動從證交所抓取所有上市、上櫃、ETF 及創新板代號。
- **數據管線**：透過 `yfinance` 進行多執行緒歷史數據下載。
- **矩陣分析**：生成 9 張分佈圖表，完整呈現市場健康狀態。
- **專業報表**：透過 **Resend API** 寄送 HTML 郵件，包含彩色排版表格與直達 **玩股網技術線圖** 的超連結。
- **雲端自動化**：完全基於 GitHub Actions，定時觸發執行（台北時間 13:30/14:00）。

### 🧰 技術棧
- **程式語言**：Python 3.10
- **函式庫**：Pandas, Matplotlib, Requests, Concurrent.futures, Tqdm
- **自動化**：GitHub Actions
- **基礎設施**：Ubuntu-latest (支援 CJK 中文字體安裝)


--------------------------------------
本專案設計為利用 GitHub Actions 實現完全自動化的股票數據爬取、分析與郵件報表發送。以下是設定步驟與執行邏輯的詳細說明。

什麼是 GitHub Actions？
GitHub Actions 是一個持續整合/持續部署 (CI/CD) 工具，它可以讓你自動化軟體開發工作流程。在本專案中，我們利用它來：

定時觸發（例如每天開盤前或收盤後）。
在雲端虛擬機上執行 Python 程式碼。
將分析結果透過 Email 發送給你。 所有這些過程都無需你手動操作，完全自動化！
🤖 設定步驟 (5 分鐘快速上手)
步驟 1: Fork 本專案
登入你的 GitHub 帳號。
前往本專案頁面：https://github.com/grissomlin/taiwan-stock-monitor
點擊右上角的 Fork 按鈕，將專案複製到你的個人帳號下。
步驟 2: 設定 Resend API 金鑰 (用於郵件發送)
本專案使用 Resend 服務來發送專業報表郵件。你需要獲取一個 API 金鑰並設定為 GitHub Secrets。

註冊 Resend 帳號：前往 resend.com 註冊並登入。
驗證你的寄件 Email：在 Resend 後台，點擊 Domains 或 Verified Senders，新增並驗證你希望用來發送報表的 Email 地址 (例如：your_email@example.com)。
獲取 API Key：在 Resend 後台點擊 API Keys，創建一個新的 API Key。請記住這個 Key，它只會顯示一次。
設定 GitHub Secret：
在你的 Forked Repository 頁面，點擊 Settings。
在左側導航欄找到 Secrets > Actions。
點擊 New repository secret。
名稱 (Name) 填寫：RESEND_API_KEY
值 (Secret) 填寫你在 Resend 獲取的 API Key。
點擊 Add secret。
步驟 3: 設定收件者 Email
你需要指定接收報表的 Email 地址。這也透過 GitHub Secrets 設定。

重複上述「設定 GitHub Secret」的步驟。
名稱 (Name) 填寫：REPORT_RECEIVER_EMAIL
值 (Secret) 填寫你希望接收報表的 Email 地址 (例如：your_receiver_email@example.com)。
點擊 Add secret。
步驟 4: 觸發 Workflow 執行
本專案的 Workflow (.github/workflows/daily_report.yml) 預設會在：

每天台灣時間 上午 09:00 執行一次。
每天台灣時間 下午 05:00 執行一次。
或你可以手動觸發。
手動觸發步驟：

在你的 Forked Repository 頁面，點擊 Actions。
在左側邊欄找到 Daily Taiwan Stock Report (或你 Workflow 檔案的名稱)。
點擊 Run workflow 按鈕 (通常在右側)。
點擊綠色的 Run workflow 確認。
🔍 執行流程概覽
當 Workflow 被觸發後，GitHub Actions 會執行以下步驟：

環境設置：啟動一台 Ubuntu 虛擬機，並安裝 Python 3.10 及所有必要的套件 (requirements.txt)。
數據下載 (downloader_tw.py)：
程式會從台灣證交所 (TWSE) 爬取最新的全市場股票、ETF、DR、興櫃、創新板等標的清單 (約 2600 檔，已排除權證)。
透過 yfinance 庫，為每檔標的下載近 2 年的歷史日 K 線數據。
此步驟包含隨機延遲 (Jitter) 與自動重試機制，以有效規避數據源的頻率限制 (Rate Limiting)，確保數據的完整性。
下載的數據會以 CSV 格式儲存在 data/tw-share/dayK/ 目錄下。
數據分析與繪圖 (analyzer.py)：
讀取所有下載的日 K 數據。
計算每檔標的在過去 5 日 (週 K)、20 日 (月 K)、250 日 (年 K) 的最高漲幅、收盤漲幅、最低跌幅。
生成動態報酬分佈圖 (直方圖)，視覺化全市場的漲跌情緒。
針對每個報酬區間 (例如：> +100%、+10%~+20% 等)，整理出詳細的公司清單與股票連結。
生成並發送郵件報表 (reporter.py)：
將分析結果、圖表與公司清單整合為一份精美的 HTML 格式報告。
使用 Resend API 將此報告自動發送到你在 REPORT_RECEIVER_EMAIL Secret 中設定的 Email 地址。
📊 輸出結果預覽
你將會收到一份包含以下內容的專業郵件報告：

全市場在不同週期 (週、月、年) 的漲跌幅分佈圖。
每個漲跌幅區間內包含的股票清單，並可點擊連結查看詳細資訊。
市場總覽與關鍵統計數據。
疑難排解
Email 未收到：請檢查你的 REPORT_RECEIVER_EMAIL Secret 是否正確，並確認 Resend 後台的寄件 Email 是否已驗證。
Actions 執行失敗：檢查 GitHub Actions 的 Log 輸出，通常會有明確的錯誤訊息指示問題所在。常見問題如：API Key 未設定、網路連線錯誤等。
下載家數不足：若成功下載家數遠低於總數 (約 2600)，請檢查 Log 中是否有 Too Many Requests 或 empty 訊息，這可能需要微調 MAX_WORKERS 參數或等待時間。


![googlesheet1](image/week_close.png)



![googlesheet1](image/week_high.png)



![googlesheet1](image/week_low.png)


![googlesheet1](image/month_high.png)


![googlesheet1](image/month_low.png)


![googlesheet1](image/month_close.png)



![googlesheet1](image/year_close.png)



![googlesheet1](image/year_high.png)


![googlesheet1](image/year_low.png)


![googlesheet1](image/1.png)



![googlesheet1](image/2.png)


![googlesheet1](image/3.png)


![googlesheet1](image/4.png)



![googlesheet1](image/5.png)


![googlesheet1](image/6.png)


![googlesheet1](image/7.png)

![googlesheet1](image/8.png)




