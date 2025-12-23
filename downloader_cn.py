# -*- coding: utf-8 -*-  改用東方財富取代akshare
import os, sys, time, random, json, subprocess
import pandas as pd
import yfinance as yf
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# ========== 參數與路徑設定 ==========
MARKET_CODE = "cn-share"
DATA_SUBDIR = "dayK"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", MARKET_CODE, DATA_SUBDIR)
LIST_DIR = os.path.join(BASE_DIR, "data", MARKET_CODE, "lists")
CACHE_LIST_PATH = os.path.join(LIST_DIR, "cn_stock_list_cache.json")

# GitHub Actions 建議 thread 不要開太高，避免被 Yahoo 封鎖 IP
THREADS_CN = 4 
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LIST_DIR, exist_ok=True)

def log(msg: str):
    print(f"{pd.Timestamp.now():%H:%M:%S}: {msg}")

def ensure_pkg(pkg: str):
    try:
        __import__(pkg)
    except ImportError:
        log(f"🔧 正在安裝 {pkg}...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg])

def get_cn_list():
    """獲取 A 股清單：整合 EM 接口與多重保底機制"""
    ensure_pkg("akshare")
    import akshare as ak
    threshold = 4500  # A 股正常應有 5000+ 檔
    
    # 1. 檢查今日快取
    if os.path.exists(CACHE_LIST_PATH):
        try:
            file_mtime = os.path.getmtime(CACHE_LIST_PATH)
            if datetime.fromtimestamp(file_mtime).date() == datetime.now().date():
                with open(CACHE_LIST_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if len(data) >= threshold:
                        log(f"📦 載入今日快取 (共 {len(data)} 檔)")
                        return data
        except Exception as e:
            log(f"⚠️ 快取讀取失敗: {e}")

    # 2. 嘗試 EM 接口 (通常比標準接口穩定)
    log("📡 嘗試從 Akshare EM 接口獲取清單...")
    try:
        df_sh = ak.stock_sh_a_spot_em()
        df_sz = ak.stock_sz_a_spot_em()
        df = pd.concat([df_sh, df_sz], ignore_index=True)
        
        df['code'] = df['代码'].astype(str).str.zfill(6)
        # 過濾常見 A 股板塊 (主板、創業板、科創板)
        valid_prefixes = ('000','001','002','003','300','301','600','601','603','605','688')
        df = df[df['code'].str.startswith(valid_prefixes)]
        
        res = [f"{row['code']}&{row['名称']}" for _, row in df.iterrows()]
        
        if len(res) >= threshold:
            with open(CACHE_LIST_PATH, "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False)
            log(f"✅ 成功獲取 {len(res)} 檔標的")
            return res
    except Exception as e:
        log(f"⚠️ EM 接口失敗: {e}")

    # 3. 歷史快取保底
    if os.path.exists(CACHE_LIST_PATH):
        log("🔄 接口全數失敗，使用過期快取備援...")
        with open(CACHE_LIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    # 4. 最終保底 (核心權值股)
    log("🚨 完全無法取得清單，執行保底測試集")
    return ["600519&貴州茅台", "000001&平安銀行", "300750&寧德時代", "601318&中國平安"]

def download_one(item):
    """單檔下載邏輯：具備重試與強化防封鎖"""
    code, name = item.split('&', 1)
    # Yahoo Finance 格式
    symbol = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
    out_path = os.path.join(DATA_DIR, f"{code}_{name}.csv")

    # 續跑機制：若檔案已存在且大小正常則跳過
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1500:
        return {"status": "exists", "code": code}

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 隨機延遲 1.0~2.5 秒，模擬真人行為
            time.sleep(random.uniform(1.0, 2.5))
            
            tk = yf.Ticker(symbol)
            # 下載 2 年數據
            hist = tk.history(period="2y", timeout=25)
            
            if hist is not None and not hist.empty:
                hist.reset_index(inplace=True)
                hist.columns = [c.lower() for c in hist.columns]
                
                # 時間格式處理
                if 'date' in hist.columns:
                    hist['date'] = pd.to_datetime(hist['date'], utc=True).dt.tz_localize(None)
                
                # 儲存 CSV (utf-8-sig 確保 Excel 開啟中文不亂碼)
                hist.to_csv(out_path, index=False, encoding='utf-8-sig')
                return {"status": "success", "code": code}
            else:
                # 有些代碼可能已下市或抓不到
                if attempt == max_retries - 1:
                    return {"status": "empty", "code": code}
                
        except Exception:
            if attempt == max_retries - 1:
                return {"status": "error", "code": code}
            time.sleep(random.randint(5, 10)) # 失敗後進入冷卻再重試
            
    return {"status": "error", "code": code}

def main():
    start_time = time.time()
    log("🇨🇳 中國 A 股數據同步器啟動 (GitHub Actions 優化版)")
    
    items = get_cn_list()
    log(f"🚀 目標總數: {len(items)} 檔")
    
    stats = {"success": 0, "exists": 0, "empty": 0, "error": 0}
    
    # 使用 ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=THREADS_CN) as executor:
        futures = {executor.submit(download_one, it): it for it in items}
        pbar = tqdm(total=len(items), desc="下載進度")
        
        for f in as_completed(futures):
            res = f.result()
            stats[res.get("status", "error")] += 1
            pbar.update(1)
        
        pbar.close()

    duration = (time.time() - start_time) / 60
    log(f"📊 執行報告 (耗時 {duration:.1f} 分鐘):")
    log(f"   - 成功: {stats['success']}")
    log(f"   - 跳過(已存在): {stats['exists']}")
    log(f"   - 失敗/無數據: {stats['error'] + stats['empty']}")
    log("✨ 數據更新完成，準備進行矩陣分析...")

if __name__ == "__main__":
    main()
