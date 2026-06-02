import os
import ccxt
import pandas as pd
import requests
import asyncio
from fastapi import FastAPI
import uvicorn

# تعريف خادم الويب
app = FastAPI(title="CryptoAgent Backend")

# ==========================================
# 1. إعدادات تليجرام
# ==========================================
TOKEN = "8685536033:AAFwj2p3T8qdnM3gnt4kHAbAItXRJzuswFU"
CHAT_ID = "845538348" # استبدل هذا برقمك الخاص

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

# ==========================================
# 2. محرك الرادار والتحليل الخوارزمي
# ==========================================
class AlgorithmicOpportunityHunter:
    def __init__(self, rsi_period=14):
        self.rsi_period = rsi_period

    def calculate_rsi(self, prices):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / (loss + 1e-10) 
        return 100 - (100 / (1 + rs))

    def detect_market_structure(self, df):
        df['swing_high'] = df['high'][(df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(-1))]
        df['swing_low'] = df['low'][(df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(-1))]
        
        latest_res = df['swing_high'].dropna().iloc[-1] if not df['swing_high'].dropna().empty else None
        latest_sup = df['swing_low'].dropna().iloc[-1] if not df['swing_low'].dropna().empty else None
        
        close_1, close_2 = df['close'].iloc[-1], df['close'].iloc[-2]
        
        if latest_res and close_1 > latest_res and close_2 <= latest_res: return "صاعد 🟢"
        if latest_sup and close_1 < latest_sup and close_2 >= latest_sup: return "هابط 🔴"
        return "محايد ⚪"

    def scan_market(self, market_data):
        close_prices = market_data['close']
        rsi_val = self.calculate_rsi(close_prices).iloc[-1]
        structure = self.detect_market_structure(market_data)
        
        risk = 50
        signal = "انتظار (HOLD) ⚪"
        
        if rsi_val > 70: risk += 20; signal = "بيع (SELL) 🔴"
        elif rsi_val < 30: risk -= 20; signal = "شراء (BUY) 🟢"
            
        if "صاعد" in structure: risk -= 20; signal = "شراء قوي 🚀" if risk < 40 else "شراء (BUY) 🟢"
        elif "هابط" in structure: risk += 20; signal = "بيع قوي ⚠️" if risk > 60 else "بيع (SELL) 🔴"

        return {"signal": signal, "risk": max(0, min(100, risk)), "price": float(close_prices.iloc[-1])}

# ==========================================
# 3. محرك العمل في الخلفية (يفحص السوق تلقائياً)
# ==========================================
async def background_scanner():
    # نستخدم MEXC لتجنب الحظر على الخوادم السحابية
    exchange = ccxt.mexc({'enableRateLimit': True})
    hunter = AlgorithmicOpportunityHunter()
    target_coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']

    while True:
        try:
            telegram_message = "📊 *تحديث CryptoAgent التلقائي* 📊\n\n"
            for symbol in target_coins:
                try:
                    live_data = exchange.fetch_ohlcv(symbol, '5m', limit=100)
                    df = pd.DataFrame(live_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    report = hunter.scan_market(df)
                    
                    telegram_message += f"🔹 *{symbol}*\n"
                    telegram_message += f"▪️ السعر: `{report['price']} USDT`\n"
                    telegram_message += f"▪️ الإشارة: *{report['signal']}*\n"
                    telegram_message += f"▪️ الخطورة: {report['risk']}/100\n"
                    telegram_message += "──────────────\n"
                    
                    # توقف مؤقت لتجنب الحظر من المنصة
                    await asyncio.sleep(2)  
                except Exception as e:
                    print(f"Error fetching {symbol}: {e}")
                    telegram_message += f"🔹 *{symbol}* : ❌ تعذر الاتصال\n──────────────\n"
            
            # إرسال التقرير النهائي إلى تليجرام
            send_telegram_alert(telegram_message)
            
        except Exception as e:
            print(f"Scanner Error: {e}")
        
        # الخادم سينتظر 15 دقيقة (900 ثانية) قبل الفحص القادم
        await asyncio.sleep(900)

# ==========================================
# 4. إعدادات الخادم والمسارات (FastAPI)
# ==========================================
@app.on_event("startup")
async def startup_event():
    # بمجرد إقلاع الخادم على Render، سيرسل لك هذه الرسالة ويبدأ الفحص
    send_telegram_alert("🚀 *خادم CryptoAgent يعمل الآن بنجاح على منصة Render!* \nبدأ نظام الفحص الآلي...")
    asyncio.create_task(background_scanner())

@app.get("/")
def read_root():
    # هذه الصفحة ستخبر منصة Render أن الخادم يعمل ولا يوجد به أخطاء
    return {
        "status": "Online",
        "message": "CryptoAgent Engine is Running 24/7",
        "version": "1.0 MVP"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
