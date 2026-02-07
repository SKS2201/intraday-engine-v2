mport requests
import pandas as pd
import datetime
import os

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram secrets not set")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=20)

now = datetime.datetime.now()
if now.weekday() > 4:
    send_telegram("📴 NO TRADE DAY (Weekend)")
    raise SystemExit(0)

def fetch_preopen_nifty() -> pd.DataFrame:
    url = "https://www.nseindia.com/api/market-data-pre-open?key=NIFTY"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/",
    }
    s = requests.Session()
    s.get("https://www.nseindia.com", headers=headers, timeout=20)
    r = s.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    j = r.json()
    rows = []
    for item in j.get("data", []):
        m = item.get("metadata", {}) or {}
        sym = m.get("symbol")
        if not sym:
            continue
        rows.append({
            "symbol": sym,
            "pChange": float(m.get("pChange") or 0),
            "high": float(m.get("highPrice") or 0),
            "low": float(m.get("lowPrice") or 0),
        })
    return pd.DataFrame(rows)

try:
    df = fetch_preopen_nifty()
except Exception as e:
    send_telegram(f"⚠️ NSE Pre-open fetch failed\n{e}")
    raise SystemExit(1)

if df.empty:
    send_telegram("⚠️ NSE pre-open returned no data. NO TRADE.")
    raise SystemExit(0)

top5 = df.sort_values("pChange", ascending=False).head(5)

msg = "📊 NSE PRE-OPEN TOP 5 (Intraday Watchlist)\n\n"
for _, r in top5.iterrows():
    entry = round(r["high"] * 1.002, 2)
    sl = round(r["low"] * 0.998, 2)
    target = round(entry + (entry - sl) * 2, 2)
    msg += (
        f"🔹 {r['symbol']} (Pre-open %Chg: {r['pChange']:.2f}%)\n"
        f"Entry > {entry} (15m sustain above PDH)\n"
        f"SL: {sl}\n"
        f"Target: {target}\n\n"
    )

msg += "⚠️ Trade ONLY if 15-min candle sustains above entry.\n"
msg += "❌ If no sustain → NO TRADE.\n"
msg += "📱 Execute manually on Groww."

send_telegram(msg)
print("Alert sent successfully")
