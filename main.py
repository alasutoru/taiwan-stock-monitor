# -*- coding: utf-8 -*-
import os
import time
import argparse
import traceback
from datetime import datetime, timedelta

# 導入自定義模組
import downloader_tw
import downloader_us
import downloader_hk
import downloader_cn
import downloader_jp
import downloader_kr
import analyzer
import notifier

def run_market_pipeline(market_id, market_name, emoji):
    """
    執行單一市場的完整管線：下載 -> 分析 -> 寄信
    """
    print("\n" + "="*60)
    print(f"{emoji} 啟動管線：{market_name} ({market_id})")
    print("="*60)

    # 初始化統計變數，預設為 0
    stats = {"total": 0, "success": 0, "fail": 0}
    
    # 建立通知器實例 (用於發送 Telegram 與 Resend 郵件)
    agent = notifier.StockNotifier()

    # --- Step 1: 數據獲取 ---
    print(f"【Step 1: 數據獲取】正在更新 {market_name} 原始 K 線資料...")
    try:
        res = None
        # 根據市場 ID 呼叫對應的下載器主函數
        if market_id == "tw-share":
            res = downloader_tw.main()
        elif market_id == "us-share":
            res = downloader_us.main()
        elif market_id == "hk-share":
            res = downloader_hk.main()
        elif market_id == "cn-share":
            res = downloader_cn.main()
        elif market_id == "jp-share":
            res = downloader_jp.main()
        elif market_id == "kr-share":
            res = downloader_kr.main()
        else:
            print(f"⚠️ 未知的市場 ID: {market_id}")
            return

        # ✨ 數據標準化：對接新版下載器的 return 字典
        if isinstance(res, dict):
            stats = res
            print(f"📊 [下載報告] 總計: {stats.get('total', 0)} | 成功: {stats.get('success', 0)} | 失敗: {stats.get('fail', 0)}")
        elif res is not None and hasattr(res, '__len__'):
            # 相容舊版回傳 List 的格式
            stats = {"total": len(res), "success": len(res), "fail": 0}
            print(f"📊 [下載報告] 已獲取 {len(res)} 檔標的。")
        else:
            print(f"⚠️ {market_name} 下載器未回傳有效數據，報告可能顯示為 0。")

    except Exception as e:
        print(f"❌ {market_name} 數據下載過程發生嚴重異常: {e}")

    # --- Step 2: 數據分析 & 繪圖 ---
    print(f"\n【Step 2: 矩陣分析】正在計算 {market_name} 動能分布並生成圖表...")
    try:
        # 呼叫分析核心，這會產生 9 張矩陣圖與報酬報表
        img_paths, report_df, text_reports = analyzer.run_global_analysis(market_id=market_id)
        
        if report_df is None or report_df.empty:
            print(f"⚠️ {market_name} 分析結果為空 (可能是 CSV 資料不足)，跳過寄信步驟。")
            return
        
        print(f"✅ 分析完成！成功處理 {len(report_df)} 檔有效數據。")

        # --- Step 3: 報表發送 ---
        print(f"\n【Step 3: 報表發送】正在透過 Resend 傳送郵件...")
        
        # 將下載統計 (stats) 與分析結果一併送出
        success_sent = agent.send_stock_report(
            market_name=market_name,
            img_data=img_paths,
            report_df=report_df,
            text_reports=text_reports,
            stats=stats
        )
        
        if success_sent:
            print(f"✅ {market_name} 監控報告已成功寄達！")
        else:
            print(f"❌ {market_name} 報告寄送失敗 (請檢查 API Key 或日誌)。")

    except Exception as e:
        print(f"❌ {market_name} 分析或寄信過程出錯:\n{traceback.format_exc()}")

def main():
    parser = argparse.ArgumentParser(description="Global Stock Monitor Orchestrator")
    parser.add_argument('--market', type=str, default='all', 
                        choices=['tw-share', 'us-share', 'hk-share', 'cn-share', 'jp-share', 'kr-share', 'all'])
    args = parser.parse_args()

    start_time = time.time()
    
    # 獲取台北時間 (UTC+8) 供 Log 記錄
    now_utc8 = datetime.utcnow() + timedelta(hours=8)
    now_str = now_utc8.strftime("%Y-%m-%d %H:%M:%S")
    
    print("\n" + "🚀 " + "="*55)
    print(f"🚀 全球股市監控自動化系統啟動")
    print(f"🚀 啟動時間: {now_str} (UTC+8)")
    print(f"🚀 執行目標: {args.market}")
    print("🚀 " + "="*55 + "\n")

    # 市場配置表
    markets_config = {
        "tw-share": {"name": "台灣股市", "emoji": "🇹🇼"},
        # "hk-share": {"name": "香港股市", "emoji": "🇭🇰"},
        # "cn-share": {"name": "中國股市", "emoji": "🇨🇳"},
        # "jp-share": {"name": "日本股市", "emoji": "🇯🇵"},
        # "kr-share": {"name": "韓國股市", "emoji": "🇰🇷"},
        # "us-share": {"name": "美國股市", "emoji": "🇺🇸"}
    }

    if args.market == 'all':
        # 依序執行所有市場
        for m_id, m_info in markets_config.items():
            run_market_pipeline(m_id, m_info["name"], m_info["emoji"])
    else:
        # 執行指定市場
        m_info = markets_config.get(args.market)
        if m_info:
            run_market_pipeline(args.market, m_info["name"], m_info["emoji"])
        else:
            print(f"❌ 找不到對應的市場配置: {args.market}")

    end_time = time.time()
    total_duration = (end_time - start_time) / 60
    print("\n" + "="*60)
    print(f"🎉 任務執行完畢！總耗時: {total_duration:.2f} 分鐘")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
