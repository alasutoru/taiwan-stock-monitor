# -*- coding: utf-8 -*-
import os
import time
import requests
import pandas as pd
import yfinance as yf
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from pathlib import Path

# ========== 核心參數設定 ==========
MARKET_CODE = "tw-share"
DATA_SUBDIR = "dayK"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", MARKET_CODE, DATA_SUBDIR)

# ✅ 效能優化：針對 Yahoo 頻率限制，建議設為 3-5 以提高穩定性
MAX_WORKERS = 4 
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

def log(msg: str):
    print(f"{pd.Timestamp.now():%H:%M:%S}: {msg}")

def get_full_stock_list():
    """獲取台股全市場清單 (排除權證)"""
    url_configs = [
        {'name': 'listed', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?market=1&issuetype=1&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'dr', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=1&issuetype=J&industry_code=&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'otc', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?market=2&issuetype=4&Page=1&chklike=Y', 'suffix': '.TWO'},
        {'name': 'etf', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=1&issuetype=I&industry_code=&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'rotc', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=E&issuetype=R&industry_code=&Page=1&chklike=Y', 'suffix': '.TWO'},
        {'name': 'tw_innovation', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=C&issuetype=C&industry_code=&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'otc_innovation', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=A&issuetype=C&industry_code=&Page=1&chklike=Y', 'suffix': '.TWO'},
    ]

    all_items = []
    log("📡 正在獲取各市場清單...")
    for cfg in url_configs:
        try:
            resp = requests.get(cfg['url'], timeout=15)
            df_list = pd.read_html(StringIO(resp.text), header=0)
            if not df_list: continue
            df = df_list[0]
            for _, row in df.iterrows():
                code = str(row['有價證券代號']).strip()
                name = str(row['有價證券名稱']).strip()
                if code and '有價證券' not in code:
                    all_items.append(f"{code}{cfg['suffix']}&{name}")
        except: continue
    return list(set(all_items))

def download_stock_data(item):
    """下載核心邏輯與診斷統計"""
    yf_tkr = "Unknown"
    try:
        yf_tkr, name = item.split('&')
        safe_name = name.replace('/', '_').replace('*', '_').replace('\\', '_').replace(':', '_')
        out_path = os.path.join(DATA_DIR, f"{yf_tkr}_{safe_name}.csv")
        
        # 若檔案已存在且有效，計入 exists
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            return {"status": "exists", "tkr": yf_tkr}

        tk = yf.Ticker(yf_tkr)
        hist = tk.history(period="2y")
        
        if hist is not None and not hist.empty:
            hist.reset_index(inplace=True)
            hist.columns = [c.lower() for c in hist.columns]
            hist.to_csv(out_path, index=False, encoding='utf-8-sig')
            return {"status": "success", "tkr": yf_tkr}
        else:
            return {"status": "empty", "tkr": yf_tkr}
    except Exception as e:
        return {"status": "error", "tkr": yf_tkr, "msg": str(e)}

def main():
    items = get_full_stock_list()
    log(f"🚀 開始稽核下載任務，目標總數: {len(items)}")
    
    stats = {"success": 0, "exists": 0, "empty": 0, "error": 0}
    empty_samples = []
    error_samples = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_stock_data, it): it for it in items}
        pbar = tqdm(total=len(items), desc="下載進度")
        
        for future in as_completed(futures):
            res = future.result()
            s = res["status"]
            stats[s] += 1
            if s == "empty": empty_samples.append(res["tkr"])
            if s == "error": error_samples.append(f"{res['tkr']}({res.get('msg', 'NA')})")
            pbar.update(1)
        pbar.close()
    
    # ✅ 輸出詳細稽核報告
    print("\n" + "="*40)
    log("📊 台股數據下載稽核結果:")
    print(f"   - ✅ 新增成功: {stats['success']}")
    print(f"   - 📁 原本已存在: {stats['exists']}")
    print(f"   - 🔍 Yahoo無資料(Empty): {stats['empty']}")
    print(f"   - ❌ 執行錯誤(Error): {stats['error']}")
    print(f"   - 📈 最終有效檔案總數: {len(list(Path(DATA_DIR).glob('*.csv')))}")
    print("="*40)
    
    if empty_samples:
        log(f"💡 無資料樣本 (前10名): {', '.join(empty_samples[:10])}")
    if error_samples:
        log(f"⚠️ 錯誤樣本 (前5名): {', '.join(error_samples[:5])}")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
