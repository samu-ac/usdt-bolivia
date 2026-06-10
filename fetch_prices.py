import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import os

BOL_TZ = timezone(timedelta(hours=-4))
now_bol = datetime.now(BOL_TZ)
today_str = now_bol.strftime("%Y-%m-%d")

DAYS_ES = ["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
MONTHS_ES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
display_date = f"{DAYS_ES[now_bol.weekday()]} {now_bol.day} de {MONTHS_ES[now_bol.month-1]}, {now_bol.year}"


def fetch_binance_p2p(trade_type):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = json.dumps({
        "page": 1, "rows": 10, "payTypes": [],
        "asset": "USDT", "tradeType": trade_type,
        "fiat": "BOB", "publisherType": None
    }).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        prices = [float(ad["adv"]["price"]) for ad in data.get("data", [])[:5]]
        return round(sum(prices) / len(prices), 2) if prices else None
    except Exception as e:
        print(f"Binance P2P error ({trade_type}): {e}")
        return None


class BCBVRDParser(HTMLParser):
    """Extrae el VRD Compra del HTML de BCB."""
    def __init__(self):
        super().__init__()
        self.vrd = None
        self._in_vrd = False
        self._last_text = ""

    def handle_data(self, data):
        t = data.strip()
        if "VRD Compra" in t:
            self._in_vrd = True
        if self._in_vrd and t and t.replace(",", "").replace(".", "").isdigit():
            try:
                v = float(t.replace(",", "."))
                if 6.0 < v < 15.0:
                    self.vrd = v
                    self._in_vrd = False
            except Exception:
                pass


def fetch_bcb_vrd():
    """Intenta obtener el VRD del dia desde BCB."""
    # Formato fecha: MM/DD/YYYY en el query param de BCB
    date_param = now_bol.strftime("%m/%d/%Y")
    url = f"https://www.bcb.gob.bo/?q=content/valor-referencial-de-compra-del-dolar-estadounidense-vrd&date={date_param}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "es-BO,es;q=0.9"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        parser = BCBVRDParser()
        parser.feed(html)
        return parser.vrd
    except Exception as e:
        print(f"BCB VRD fetch error: {e}")
        return None


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── USDT P2P ──
existing = load_json("data/prices.json")
buy_price  = fetch_binance_p2p("BUY")
sell_price = fetch_binance_p2p("SELL")
if buy_price  is None and existing.get("binance"): buy_price  = existing["binance"].get("buy",  9.93)
if sell_price is None and existing.get("binance"): sell_price = existing["binance"].get("sell", 9.97)

print(f"Binance P2P - Compra: {buy_price} | Venta: {sell_price}")

history = existing.get("history", [])
history = [h for h in history if h["date"] != today_str]
history.append({"date": today_str, "buy": buy_price, "sell": sell_price})
history = sorted(history, key=lambda x: x["date"])

output = {
    "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "displayDate": display_date,
    "binance":  {"buy": buy_price,  "sell": sell_price, "available": buy_price is not None},
    "airtm":    {"buy": round(buy_price*0.996,2) if buy_price else None, "sell": round(sell_price*0.997,2) if sell_price else None, "available": buy_price is not None},
    "eldorado": {"buy": round(buy_price*1.004,2) if buy_price else None, "sell": round(sell_price*0.993,2) if sell_price else None, "available": buy_price is not None},
    "takenos":  {"buy": round(buy_price*1.019,2) if buy_price else None, "sell": round(sell_price*0.990,2) if sell_price else None, "available": buy_price is not None},
    "wallbit":  {"buy": round(buy_price*1.009,2) if buy_price else None, "sell": round(sell_price*0.989,2) if sell_price else None, "available": buy_price is not None},
    "bcb": existing.get("bcb", {"officialBuy": 6.86, "officialSell": 6.96, "referentialBuy": 9.86, "referentialSell": 10.07}),
    "history": history
}
save_json("data/prices.json", output)
print("prices.json actualizado.")

# ── BCB VRD ──
vrd_data = load_json("data/bcb_vrd.json")
vrd_history = vrd_data.get("history", [])

vrd_today = fetch_bcb_vrd()
if vrd_today:
    print(f"BCB VRD hoy: {vrd_today}")
    vrd_history = [h for h in vrd_history if h["date"] != today_str]
    vrd_history.append({"date": today_str, "vrd": vrd_today})
    vrd_history = sorted(vrd_history, key=lambda x: x["date"])
else:
    print("BCB VRD no disponible hoy, usando datos guardados.")
    vrd_today = vrd_data.get("vrd_today", 9.86)

vrd_output = {
    "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "today":       today_str,
    "vrd_today":   vrd_today,
    "history":     vrd_history
}
save_json("data/bcb_vrd.json", vrd_output)
print("bcb_vrd.json actualizado.")
