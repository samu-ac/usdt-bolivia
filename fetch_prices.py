import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import os
import sys

# UTF-8 para evitar errores de encoding en Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BOL_TZ = timezone(timedelta(hours=-4))
now_bol = datetime.now(BOL_TZ)
today_str = now_bol.strftime("%Y-%m-%d")

DAYS_ES   = ["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
MONTHS_ES = ["enero","febrero","marzo","abril","mayo","junio","julio",
             "agosto","septiembre","octubre","noviembre","diciembre"]
display_date = (f"{DAYS_ES[now_bol.weekday()]} {now_bol.day} "
                f"de {MONTHS_ES[now_bol.month-1]}, {now_bol.year}")

# ── API Keys desde GitHub Secrets (env vars) ──────────────────────────────
# Para activarlas: GitHub repo -> Settings -> Secrets -> Actions -> New secret
ELDORADO_API_KEY = os.environ.get("ELDORADO_API_KEY", "")
WALLBIT_API_KEY  = os.environ.get("WALLBIT_API_KEY",  "")

# ── Multiplicadores confirmados (fallback cuando no hay API) ───────────────
# Fuente: observaciones reales del mercado boliviano, validadas por el usuario
# Base = precio compra Binance P2P
FALLBACK = {
    "eldorado": {"buyMult": 1.0071, "sellMult": 0.9880},  # buy=10.00, sell=9.85
    "takenos":  {"buyMult": 1.0222, "sellMult": 0.9860},  # buy=10.15, sell=9.83
    "wallbit":  {"buyMult": 1.0121, "sellMult": 0.9840},  # buy=10.05, sell=9.81
    "airtm":    {"buyMult": 1.0161, "sellMult": 0.9709},  # buy=10.09, sell=9.68
}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
}


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS HTTP
# ─────────────────────────────────────────────────────────────────────────────
def http_get(url, timeout=15, extra_headers=None):
    h = dict(HEADERS)
    if extra_headers:
        h.update(extra_headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"    GET {url[:60]}... error: {e}")
        return None


def http_post_json(url, payload, timeout=15):
    body = json.dumps(payload).encode()
    h = dict(HEADERS)
    h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"    POST {url[:60]}... error: {e}")
        return None


def extract_buy_sell(d):
    """Busca buy/sell en un dict con nombres comunes de campo."""
    for node in [d, d.get("data", {}), d.get("rates", {}),
                 d.get("quote", {}), d.get("result", {})]:
        if not isinstance(node, dict):
            continue
        b = node.get("buy") or node.get("buyPrice") or node.get("buy_price")
        s = node.get("sell") or node.get("sellPrice") or node.get("sell_price")
        if b and s:
            b, s = float(b), float(s)
            if 7 < b < 20 and 7 < s < 20:
                return round(b, 2), round(s, 2)
    return None, None


def calc_fallback(base_buy, base_sell, key):
    m = FALLBACK[key]
    return {
        "buy":       round(base_buy  * m["buyMult"],  2),
        "sell":      round(base_sell * m["sellMult"], 2),
        "available": True,
        "source":    "calculated",
    }


# ─────────────────────────────────────────────────────────────────────────────
#  1. BINANCE P2P  (directo desde el servidor, sin CORS)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_binance_p2p(trade_type):
    data = http_post_json(
        "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
        {"page": 1, "rows": 10, "payTypes": [], "asset": "USDT",
         "tradeType": trade_type, "fiat": "BOB", "publisherType": None}
    )
    if not data:
        return None
    prices = [float(ad["adv"]["price"]) for ad in data.get("data", [])[:5]]
    return round(sum(prices) / len(prices), 2) if prices else None


# ─────────────────────────────────────────────────────────────────────────────
#  2. DOLAR BLUE BOLIVIA API  (tasa paralela + BCB oficial)
#     https://api.dolarbluebolivia.click/v1/officialRate
# ─────────────────────────────────────────────────────────────────────────────
def fetch_dolar_blue_api():
    raw = http_get("https://api.dolarbluebolivia.click/v1/officialRate")
    if not raw:
        return None
    try:
        return json.loads(raw).get("data")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  3. EL DORADO  — API oficial
#     Docs: https://api.eldorado.io/
#     Para activar: crea cuenta en eldorado.io, ve a Developer/API,
#     genera tu API Key y guardala como secret ELDORADO_API_KEY en GitHub.
# ─────────────────────────────────────────────────────────────────────────────
def fetch_eldorado():
    endpoints = [
        "https://api.eldorado.io/v1/rates?fiat=BOB&crypto=USDT",
        "https://api.eldorado.io/v1/quotes?fiat=BOB&crypto=USDT",
        "https://api.eldorado.io/v2/market/rates?fiat=BOB&crypto=USDT",
        "https://api.eldorado.io/v2/rates?fiat=BOB&crypto=USDT",
    ]
    extra = {"Origin": "https://eldorado.io", "Referer": "https://eldorado.io/"}
    if ELDORADO_API_KEY:
        extra["Authorization"] = f"Bearer {ELDORADO_API_KEY}"
        extra["X-API-Key"]     = ELDORADO_API_KEY
        print("  El Dorado: usando API Key")
    else:
        print("  El Dorado: sin API Key (intento publico)")

    for url in endpoints:
        raw = http_get(url, extra_headers=extra)
        if not raw:
            continue
        try:
            d = json.loads(raw)
            b, s = extract_buy_sell(d)
            if b and s:
                src = "api_eldorado" if ELDORADO_API_KEY else "api_eldorado_public"
                print(f"  El Dorado OK -> compra={b} venta={s} [{src}]")
                return {"buy": b, "sell": s, "available": True, "source": src}
        except Exception as e:
            print(f"  El Dorado parse error: {e}")

    print("  El Dorado: API no disponible -> multiplicadores")
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  4. WALLBIT  — API "for Agents"
#     Docs: https://help.wallbit.io/es/articles/13706842-api-publica-wallbit-for-agents
#     Para activar: registrate en developer.wallbit.io, crea un Agente,
#     genera API Key y guardala como secret WALLBIT_API_KEY en GitHub.
# ─────────────────────────────────────────────────────────────────────────────
def fetch_wallbit():
    endpoints = [
        "https://api.wallbit.io/api/public/v1/rates?fiat=BOB",
        "https://api.wallbit.io/api/public/v1/crypto/rates?symbol=USDT&fiat=BOB",
        "https://api.wallbit.io/api/public/v1/price?asset=USDT&fiat=BOB",
        "https://api.wallbit.io/api/v1/crypto/price?symbol=USDT&fiat=BOB",
    ]
    extra = {"Origin": "https://wallbit.io", "Referer": "https://wallbit.io/"}
    if WALLBIT_API_KEY:
        extra["X-API-Key"]     = WALLBIT_API_KEY
        extra["Authorization"] = f"Bearer {WALLBIT_API_KEY}"
        print("  Wallbit: usando API Key")
    else:
        print("  Wallbit: sin API Key (intento publico)")

    for url in endpoints:
        raw = http_get(url, extra_headers=extra)
        if not raw:
            continue
        try:
            d = json.loads(raw)
            b, s = extract_buy_sell(d)
            if b and s:
                src = "api_wallbit" if WALLBIT_API_KEY else "api_wallbit_public"
                print(f"  Wallbit OK -> compra={b} venta={s} [{src}]")
                return {"buy": b, "sell": s, "available": True, "source": src}
        except Exception as e:
            print(f"  Wallbit parse error: {e}")

    print("  Wallbit: API no disponible -> multiplicadores")
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  5. BCB VRD  — scraping bcb.gob.bo
# ─────────────────────────────────────────────────────────────────────────────
class BCBVRDParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.vrd = None
        self._capture = False

    def handle_data(self, data):
        t = data.strip()
        if "VRD Compra" in t or "Valor Referencial" in t:
            self._capture = True
        if self._capture and t and t.replace(",", "").replace(".", "").isdigit():
            try:
                v = float(t.replace(",", "."))
                if 6.0 < v < 15.0:
                    self.vrd = v
                    self._capture = False
            except Exception:
                pass


def fetch_bcb_vrd():
    date_param = now_bol.strftime("%m/%d/%Y")
    url = (f"https://www.bcb.gob.bo/?q=content/"
           f"valor-referencial-de-compra-del-dolar-estadounidense-vrd"
           f"&date={date_param}")
    raw = http_get(url, timeout=20,
                   extra_headers={"Accept": "text/html,application/xhtml+xml"})
    if not raw:
        return None
    try:
        p = BCBVRDParser()
        p.feed(raw.decode("utf-8", errors="ignore"))
        return p.vrd
    except Exception as e:
        print(f"  BCB VRD parse error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS I/O
# ─────────────────────────────────────────────────────────────────────────────
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =============================================================================
#  MAIN
# =============================================================================
existing = load_json("data/prices.json")

# ── 1. Binance P2P ──
print("Obteniendo Binance P2P...")
buy_price  = fetch_binance_p2p("BUY")
sell_price = fetch_binance_p2p("SELL")
if buy_price  is None: buy_price  = existing.get("binance", {}).get("buy",  9.93)
if sell_price is None: sell_price = existing.get("binance", {}).get("sell", 9.97)
print(f"  Binance P2P -> Compra: {buy_price} | Venta: {sell_price}")

# ── 2. BCB Oficial (via DolarBlue API) ──
print("Obteniendo BCB / DolarBlue API...")
dolar_blue = fetch_dolar_blue_api()
if dolar_blue and dolar_blue.get("official"):
    bcb_data = {
        "officialBuy":     dolar_blue["official"]["buy"],
        "officialSell":    dolar_blue["official"]["sell"],
        "referentialBuy":  dolar_blue.get("blue", {}).get("buy",  buy_price),
        "referentialSell": dolar_blue.get("blue", {}).get("sell", sell_price),
    }
    print(f"  BCB Oficial -> Compra: {bcb_data['officialBuy']} | Venta: {bcb_data['officialSell']}")
else:
    bcb_data = existing.get("bcb", {
        "officialBuy": 6.86, "officialSell": 6.96,
        "referentialBuy": 9.86, "referentialSell": 10.07
    })
    print("  DolarBlue API no disponible -> usando datos guardados")

# ── 3. El Dorado ──
print("Obteniendo El Dorado...")
eldorado_data = fetch_eldorado() or calc_fallback(buy_price, sell_price, "eldorado")

# ── 4. Wallbit ──
print("Obteniendo Wallbit...")
wallbit_data = fetch_wallbit() or calc_fallback(buy_price, sell_price, "wallbit")

# ── 5. Takenos y AirTM (solo multiplicadores — sin API publica) ──
takenos_data = calc_fallback(buy_price, sell_price, "takenos")
airtm_data   = calc_fallback(buy_price, sell_price, "airtm")
print(f"  Takenos (calc) -> Compra: {takenos_data['buy']} | Venta: {takenos_data['sell']}")
print(f"  AirTM   (calc) -> Compra: {airtm_data['buy']}  | Venta: {airtm_data['sell']}")

# ── Historial USDT ──
history = existing.get("history", [])
history = [h for h in history if h["date"] != today_str]
history.append({"date": today_str, "buy": buy_price, "sell": sell_price})
history = sorted(history, key=lambda x: x["date"])

save_json("data/prices.json", {
    "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "displayDate": display_date,
    "binance":  {"buy": buy_price,  "sell": sell_price, "available": True,  "source": "binance_p2p"},
    "eldorado": eldorado_data,
    "takenos":  takenos_data,
    "wallbit":  wallbit_data,
    "airtm":    airtm_data,
    "bybit":    {"buy": round(buy_price*1.0, 2),   "sell": round(sell_price*1.0, 2),   "available": True, "source": "calculated"},
    "saldoar":  {"buy": round(buy_price*1.011, 2), "sell": round(sell_price*0.988, 2), "available": True, "source": "calculated"},
    "bcb":      bcb_data,
    "history":  history
})
print("prices.json actualizado.")

# ── BCB VRD ──
print("Obteniendo BCB VRD...")
vrd_data    = load_json("data/bcb_vrd.json")
vrd_history = vrd_data.get("history", [])
vrd_today   = fetch_bcb_vrd()
if vrd_today:
    print(f"  BCB VRD hoy: {vrd_today}")
    vrd_history = [h for h in vrd_history if h["date"] != today_str]
    vrd_history.append({"date": today_str, "vrd": vrd_today})
    vrd_history = sorted(vrd_history, key=lambda x: x["date"])
else:
    print("  BCB VRD no disponible hoy -> usando dato guardado")
    vrd_today = vrd_data.get("vrd_today", 9.86)

save_json("data/bcb_vrd.json", {
    "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "today":     today_str,
    "vrd_today": vrd_today,
    "history":   vrd_history
})
print("bcb_vrd.json actualizado.")

print("\n=== RESUMEN FINAL ===")
print(f"  Binance P2P  -> Compra: {buy_price}  | Venta: {sell_price}")
print(f"  El Dorado    -> Compra: {eldorado_data['buy']} | Venta: {eldorado_data['sell']} [{eldorado_data['source']}]")
print(f"  Takenos      -> Compra: {takenos_data['buy']} | Venta: {takenos_data['sell']} [calculated]")
print(f"  Wallbit      -> Compra: {wallbit_data['buy']} | Venta: {wallbit_data['sell']} [{wallbit_data['source']}]")
print(f"  AirTM        -> Compra: {airtm_data['buy']}  | Venta: {airtm_data['sell']} [calculated]")
print(f"  BCB Oficial  -> Compra: {bcb_data['officialBuy']} | Venta: {bcb_data['officialSell']}")
print(f"  BCB VRD      -> {vrd_today}")
