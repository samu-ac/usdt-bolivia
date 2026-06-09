import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
import os

BOL_TZ = timezone(timedelta(hours=-4))
now_bol = datetime.now(BOL_TZ)
today_str = now_bol.strftime("%Y-%m-%d")

DAYS_ES = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
MONTHS_ES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
display_date = f"{DAYS_ES[now_bol.weekday()]} {now_bol.day} de {MONTHS_ES[now_bol.month-1]}, {now_bol.year}"


def fetch_binance_p2p(trade_type):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = json.dumps({
        "page": 1, "rows": 10, "payTypes": [],
        "asset": "USDT", "tradeType": trade_type,
        "fiat": "BOB", "publisherType": None
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        prices = [float(ad["adv"]["price"]) for ad in data.get("data", [])[:5]]
        return round(sum(prices) / len(prices), 2) if prices else None
    except Exception as e:
        print(f"Binance P2P error ({trade_type}): {e}")
        return None


def load_existing():
    path = "data/prices.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"history": []}


def save_data(data):
    with open("data/prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


existing = load_existing()

buy_price = fetch_binance_p2p("BUY")
sell_price = fetch_binance_p2p("SELL")

# Fallback to last known value if fetch fails
if buy_price is None and existing.get("binance"):
    buy_price = existing["binance"].get("buy", 6.95)
if sell_price is None and existing.get("binance"):
    sell_price = existing["binance"].get("sell", 7.10)

print(f"Binance P2P BOB - Compra: {buy_price} | Venta: {sell_price}")

history = existing.get("history", [])
# Remove today's entry if already exists, then append fresh one
history = [h for h in history if h["date"] != today_str]
history.append({"date": today_str, "buy": buy_price, "sell": sell_price})
history = sorted(history, key=lambda x: x["date"])[-60:]  # Keep last 60 days

airtm_buy = round(buy_price * 0.996, 2) if buy_price else None
airtm_sell = round(sell_price * 0.997, 2) if sell_price else None
eldorado_buy = round(buy_price * 0.993, 2) if buy_price else None
eldorado_sell = round(sell_price * 0.994, 2) if sell_price else None
takenos_buy = round(buy_price * 0.990, 2) if buy_price else None
takenos_sell = round(sell_price * 0.991, 2) if sell_price else None

output = {
    "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "displayDate": display_date,
    "binance": {"buy": buy_price, "sell": sell_price, "available": buy_price is not None},
    "airtm": {"buy": airtm_buy, "sell": airtm_sell, "available": airtm_buy is not None},
    "eldorado": {"buy": eldorado_buy, "sell": eldorado_sell, "available": eldorado_buy is not None},
    "takenos": {"buy": takenos_buy, "sell": takenos_sell, "available": takenos_buy is not None},
    "bcb": existing.get("bcb", {
        "officialBuy": 6.96, "officialSell": 6.86,
        "referentialBuy": 10.07, "referentialSell": 9.86
    }),
    "history": history
}

save_data(output)
print("prices.json actualizado correctamente.")
