# -*- coding: utf-8 -*-
import os
import requests
import resend
import pandas as pd
from datetime import datetime, timedelta

class StockNotifier:
    def __init__(self):
        # 從環境變數讀取
        self.tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        self.receiver_email = os.getenv("REPORT_RECEIVER_EMAIL")        
        if self.resend_api_key:
            resend.api_key = self.resend_api_key

    def get_now_time_str(self):
        """獲取 UTC+8 台北時間"""
        now_utc8 = datetime.utcnow() + timedelta(hours=8)
        return now_utc8.strftime("%Y-%m-%d %H:%M:%S")

    def send_telegram(self, message):
        """發送 Telegram 即時簡報"""
        if not self.tg_token or not self.tg_chat_id: return False
        ts = self.get_now_time_str().split(" ")[1]
        full_message = f"{message}\n\n🕒 <i>Sent at {ts} (UTC+8)</i>"
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.tg_chat_id, "text": full_message, "parse_mode": "HTML"}, timeout=10)
            return True
        except: return False

    def send_stock_report(self, market_name, img_data, report_df, text_reports, stats=None):
        """🚀 專業版：寄送 HTML 報表"""
        print(f"DEBUG: notifier 正在處理 {market_name} 報告 (Stats: {stats})")

        if not self.resend_api_key:
            print("⚠️ 缺少 Resend API Key，無法寄信。 সন")
            return False

        report_time = self.get_now_time_str()
        if stats is None: stats = {}
        total_count = stats.get('total', len(report_df))
        success_count = stats.get('success', len(report_df))
        
        try:
            total_val, success_val = int(total_count), int(success_count)
            success_rate = f"{(success_val / total_val) * 100:.1f}%" if total_val > 0 else "0.0%"
        except:
            success_rate = "N/A"

        # 平台跳轉連結
        m_id = market_name.lower()
        if "us" in m_id or "美國" in market_name: p_name, p_url = "StockCharts", "https://stockcharts.com/"
        elif "hk" in m_id or "香港" in market_name: p_name, p_url = "AASTOCKS", "http://www.aastocks.com/"
        elif "cn" in m_id or "中國" in market_name: p_name, p_url = "東方財富網", "https://www.eastmoney.com/"
        elif "jp" in m_id or "日本" in market_name: p_name, p_url = "樂天證券", "https://www.rakuten-sec.co.jp/"
        elif "kr" in m_id or "韓國" in market_name: p_name, p_url = "Naver Finance", "https://finance.naver.com/"
        else: p_name, p_url = "玩股網 (WantGoo)", "https://www.wantgoo.com/"

        html_content = f"""
        <html>
        <body style="font-family: 'Microsoft JhengHei', sans-serif; color: #333;">
            <div style="max-width: 800px; margin: auto; border: 1px solid #ddd; border-top: 10px solid #28a745; padding: 25px;">
                <h2 style="color: #1a73e8;">{market_name} 全方位監控報告</h2>
                <p>生成時間: <b>{report_time} (台北時間)</b></p>
                <div style="background-color: #f8f9fa; padding: 15px; margin: 20px 0; display: flex; text-align: center;">
                    <div style="flex: 1;">應收標的<br><b>{total_count}</b></div>
                    <div style="flex: 1; border-left: 1px solid #eee;">更新成功<br><b style="color: #28a745;">{success_count}</b></div>
                    <div style="flex: 1; border-left: 1px solid #eee;">今日覆蓋率<br><b style="color: #1a73e8;">{success_rate}</b></div>
                </div>
                <p>💡 提示：可至 <a href="{p_url}" target="_blank">{p_name}</a> 查看即時技術線圖。</p>
        """

        for img in img_data:
            html_content += f"""
            <div style="margin-bottom: 40px; text-align: center;">
                <h3 style="text-align: left; border-left: 4px solid #3498db; padding-left: 10px;">📍 {img['label']}</h3>
                <img src="cid:{img['id']}" style="width: 100%; max-width: 750px;">
            </div>"""

        for period, report in text_reports.items():
            p_zh = {"Week": "週", "Month": "月", "Year": "年"}.get(period, period)
            html_content += f"""
            <div style="margin-bottom: 20px;">
                <h4 style="color: #16a085;">📊 {p_zh} K線報酬分布明細</h4>
                <pre style="background-color: #2d3436; color: #dfe6e9; padding: 15px; font-size: 12px; white-space: pre-wrap;">{report}</pre>
            </div>"""

        html_content += "</div></body></html>"

        attachments = []
        for img in img_data:
            if os.path.exists(img['path']):
                with open(img['path'], "rb") as f:
                    attachments.append({"content": list(f.read()), "filename": f"{img['id']}.png", "content_id": img['id'], "disposition": "inline"})

        # --- 關鍵修正：檢查信箱並強制轉為字串 ---
        if not self.receiver_email:
            print("❌ 錯誤：未設定收件人信箱 (REPORT_RECEIVER_EMAIL)。無法寄信。 সন")
            return False

        try:
            resend.Emails.send({
                "from": "StockMonitor <onboarding@resend.dev>",
                "to": str(self.receiver_email),
                "subject": f"🚀 {market_name} 全方位監控報告 - {report_time.split(' ')[0]}",
                "html": html_content,
                "attachments": attachments
            })
            print(f"✅ {market_name} 郵件報告已寄送！")
            self.send_telegram(f"📊 <b>{market_name} 監控報表已送達</b>\n涵蓋率: {success_rate}")
            return True
        except Exception as e:
            print(f"❌ 寄送失敗: {e}")
            return False
