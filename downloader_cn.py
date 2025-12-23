# -*- coding: utf-8 -*-
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

# 🚀 稍微提升並行數，8 是 GitHub Actions 穩定的上限
THREADS_CN = 8 
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
    threshold = 4500  
    
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

    log("📡 嘗試從 Akshare EM 接口獲取清單...")
    try:
        df_sh = ak.stock_sh_a_spot_em()
        df_sz = ak.stock_sz_a_spot_em()
        df = pd.concat([df_sh, df_sz], ignore_index=True)
        
        df['code'] = df['代码'].astype(str).str.zfill(6)
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

    if os.path.exists(CACHE_LIST_PATH):
        log("🔄 接口全數失敗，使用歷史快取備援...")
        with open(CACHE_LIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    return ["600519&貴州茅台", "000001&平安銀行", "300750&寧德時代", "601318&中國平安"]

def download_one(item):
    """單檔下載邏輯：優化隨機延遲以縮短總耗時"""
    code, name = item.split('&', 1)
    symbol = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
    out_path = os.path.join(DATA_DIR, f"{code}_{name}.csv")

    # 🚀 強化續跑判斷，若檔案存在且有內容則跳過
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        return {"status": "exists", "code": code}

    max_retries = 2
    for attempt in range(max_retries):
        try:
            # 🚀 縮短隨機等待時間，大幅提升整體速度
            time.sleep(random.uniform(0.4, 1.0)) 
            
            tk = yf.Ticker(symbol)
            hist = tk.history(period="2y", timeout=20)
            
            if hist is not None and not hist.empty:
                hist.reset_index(inplace=True)
                hist.columns = [c.lower() for c in hist.columns]
                if 'date' in hist.columns:
                    hist['date'] = pd.to_datetime(hist['date'], utc=True).dt.tz_localize(None)
                
                hist.to_csv(out_path, index=False, encoding='utf-8-sig')
                return {"status": "success", "code": code}
            else:
                if attempt == max_retries - 1:
                    return {"status": "empty", "code": code}
                
        except Exception:
            if attempt == max_retries - 1:
                return {"status": "error", "code": code}
            time.sleep(2) 
            
    return {"status": "error", "code": code}

def main():
    start_time = time.time()
    log("🇨🇳 中國 A 股數據同步器啟動 (並行度優化版)")
    
    items = get_cn_list()
    log(f"🚀 目標總數: {len(items)} 檔")
    
    stats = {"success": 0, "exists": 0, "empty": 0, "error": 0}
    
    with ThreadPoolExecutor(max_workers=THREADS_CN) as executor:
        futures = {executor.submit(download_one, it): it for it in items}
        pbar = tqdm(total=len(items), desc="下載進度")
        
        for f in as_completed(futures):
            res = f.result()
            stats[res.get("status", "error")] += 1
            pbar.update(1)
        
        pbar.close()

    # 🚀 準備統計數據供回傳
    total_expected = len(items)
    effective_success = stats['success'] + stats['exists']
    fail_count = stats['error'] + stats['empty']

    download_stats = {
        "total": total_expected,
        "success": effective_success,
        "fail": fail_count
    }

    duration = (time.time() - start_time) / 60
    log(f"📊 執行報告 (耗時 {duration:.1f} 分鐘):")
    log(f"   - 應收總數: {total_expected}")
    log(f"   - 成功(含舊檔): {effective_success}")
    log(f"   - 失敗/無數據: {fail_count}")
    log(f"📈 數據完整度: {(effective_success/total_expected)*100:.2f}%")
    
    return download_stats # 🚀 確保 main() 回傳統計，供 notifier 使用

if __name__ == "__main__":
    main()
