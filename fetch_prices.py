import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import re
import os
import sys

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

# Base URL de la API de DolarBlueBolivia
DBB = "https://api.dolarbluebolivia.click"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json",
    "Origin":   "https://dolarbluebolivia.click",
    "Referer":  "https://dolarbluebolivia.click/",
}


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def api_get(endpoint, timeout=12):
    """GET a DolarBlueBolivia API. Devuelve data{} o None."""
    req = urllib.request.Request(DBB + endpoint, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read())
            return body.get("data", body)
    except Exception as e:
        print(f"  ERROR {endpoint}: {e}")
        return None


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def plat(buy, sell, source):
    return {"buy": round(buy, 2), "sell": round(sell, 2),
            "available": True, "source": source}


# ─────────────────────────────────────────────────────────────────────────────
#  BINANCE P2P  (directo, sin CORS en el servidor)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_binance_p2p(trade_type):
    body = json.dumps({
        "page": 1, "rows": 10, "payTypes": [], "asset": "USDT",
        "tradeType": trade_type, "fiat": "BOB", "publisherType": None
    }).encode()
    h = dict(HEADERS)
    h["Content-Type"] = "application/json"
    req = urllib.request.Request(
        "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
        data=body, headers=h, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        prices = [float(ad["adv"]["price"]) for ad in data.get("data", [])[:5]]
        return round(sum(prices) / len(prices), 2) if prices else None
    except Exception as e:
        print(f"  Binance P2P error ({trade_type}): {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  BCB VRD  — scraping directo bcb.gob.bo como respaldo
# ─────────────────────────────────────────────────────────────────────────────
class BCBParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.vrd = None
        self._cap = False

    def handle_data(self, data):
        t = data.strip()
        if "VRD Compra" in t or "Valor Referencial" in t:
            self._cap = True
        if self._cap and t and t.replace(",", "").replace(".", "").isdigit():
            try:
                v = float(t.replace(",", "."))
                if 6.0 < v < 15.0:
                    self.vrd = v
                    self._cap = False
            except Exception:
                pass


def fetch_bcb_vrd_direct():
    date_param = now_bol.strftime("%m/%d/%Y")
    url = (f"https://www.bcb.gob.bo/?q=content/"
           f"valor-referencial-de-compra-del-dolar-estadounidense-vrd"
           f"&date={date_param}")
    h = dict(HEADERS)
    h["Accept"] = "text/html,application/xhtml+xml"
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="ignore")
        p = BCBParser()
        p.feed(html)
        return p.vrd
    except Exception as e:
        print(f"  BCB direct error: {e}")
        return None


# =============================================================================
#  MAIN
# =============================================================================
existing = load_json("data/prices.json")
print(f"Fecha Bolivia: {display_date}")
print()

# ── DolarBlueBolivia API — fuente principal ────────────────────────────────
print("1. DolarBlueBolivia (fuente principal)...")
d_official = api_get("/v1/officialRate")

if d_official and d_official.get("blue"):
    buy_price  = round(float(d_official["blue"]["buy"]),  2)
    sell_price = round(float(d_official["blue"]["sell"]), 2)
    print(f"   Compra: {buy_price} | Venta: {sell_price}  [dolarblue_api]")
else:
    # Fallback a Binance P2P solo si la API falla
    print("   DolarBlueBolivia no disponible, usando Binance P2P como respaldo...")
    buy_price  = fetch_binance_p2p("BUY")
    sell_price = fetch_binance_p2p("SELL")
    if buy_price  is None: buy_price  = existing.get("binance", {}).get("buy",  9.93)
    if sell_price is None: sell_price = existing.get("binance", {}).get("sell", 9.97)
    print(f"   Compra: {buy_price} | Venta: {sell_price}  [binance_p2p_fallback]")

# ── Plataformas via DolarBlueBolivia API ──────────────────────────────────
print("\n2. Plataformas (DolarBlueBolivia API)...")

# d_official ya fue obtenido arriba
d_eldorado = api_get("/v1/eldorado")
d_takenos  = api_get("/v1/takenos")
d_wallbit  = api_get("/v1/wallbit")
d_airtm    = api_get("/v1/airtm")
d_bybit    = api_get("/v1/p2p/bybit")
d_saldoar  = api_get("/v1/saldoar")
d_bcb_vrd  = api_get("/v1/referencial/bcb")

# El Dorado
if d_eldorado and d_eldorado.get("buy") and d_eldorado.get("sell"):
    eldorado_data = plat(d_eldorado["buy"], d_eldorado["sell"], "api_dbb_eldorado")
else:
    eldorado_data = plat(round(buy_price*1.0071,2), round(sell_price*0.9880,2), "calculated")
print(f"   El Dorado  Compra: {eldorado_data['buy']} | Venta: {eldorado_data['sell']}  [{eldorado_data['source']}]")

# Takenos
if d_takenos and d_takenos.get("buy") and d_takenos.get("sell"):
    takenos_data = plat(d_takenos["buy"], d_takenos["sell"], "api_dbb_takenos")
else:
    takenos_data = plat(round(buy_price*1.0222,2), round(sell_price*0.9860,2), "calculated")
print(f"   Takenos    Compra: {takenos_data['buy']} | Venta: {takenos_data['sell']}  [{takenos_data['source']}]")

# Wallbit
if d_wallbit and d_wallbit.get("buy") and d_wallbit.get("sell"):
    wallbit_data = plat(d_wallbit["buy"], d_wallbit["sell"], "api_dbb_wallbit")
else:
    wallbit_data = plat(round(buy_price*1.0121,2), round(sell_price*0.9840,2), "calculated")
print(f"   Wallbit    Compra: {wallbit_data['buy']} | Venta: {wallbit_data['sell']}  [{wallbit_data['source']}]")

# AirTM  (usa addValue/withdrawValue)
if d_airtm and d_airtm.get("addValue") and d_airtm.get("withdrawValue"):
    airtm_data = plat(d_airtm["addValue"], d_airtm["withdrawValue"], "api_dbb_airtm")
else:
    airtm_data = plat(round(buy_price*1.0161,2), round(sell_price*0.9709,2), "calculated")
print(f"   AirTM      Compra: {airtm_data['buy']} | Venta: {airtm_data['sell']}  [{airtm_data['source']}]")

# Bybit P2P
if d_bybit and d_bybit.get("buy") and float(d_bybit.get("buy",0)) > 1:
    bybit_data = plat(d_bybit["buy"], d_bybit["sell"], "api_dbb_bybit")
else:
    bybit_data = plat(round(buy_price*1.0,2), round(sell_price*1.0,2), "calculated")
print(f"   Bybit P2P  Compra: {bybit_data['buy']} | Venta: {bybit_data['sell']}  [{bybit_data['source']}]")

# SaldoAr
if d_saldoar and d_saldoar.get("buy") and d_saldoar.get("sell"):
    saldoar_data = plat(d_saldoar["buy"], d_saldoar["sell"], "api_dbb_saldoar")
else:
    saldoar_data = plat(round(buy_price*1.011,2), round(sell_price*0.988,2), "calculated")
print(f"   SaldoAr    Compra: {saldoar_data['buy']} | Venta: {saldoar_data['sell']}  [{saldoar_data['source']}]")

# ── Bancos Bolivia (pizarras) ──────────────────────────────────────────────
print("\n2b. Bancos pizarras...")
d_bancos = api_get("/v1/bancos")
banks_data = []
# IDs de los 9 bancos que queremos mostrar (en orden de presentación)
BANCOS_TARGET = ["fie","bcp","bnb","bisa","economico","union","mercantil","bancosol","ganadero"]
BANCOS_NOMBRE = {
    "fie": "Banco FIE", "bcp": "BCP", "bnb": "BNB", "bisa": "Banco Bisa",
    "economico": "Banco Económico", "union": "Banco Unión",
    "mercantil": "Mercantil Santa Cruz", "bancosol": "BancoSol",
    "ganadero": "Banco Ganadero",
}
if d_bancos:
    # La API devuelve data.bancos[].pizarra.{compra,venta}
    api_bancos = {b["id"]: b for b in d_bancos.get("bancos", [])}
    for bid in BANCOS_TARGET:
        b = api_bancos.get(bid)
        if not b:
            continue
        piz  = b.get("pizarra") or {}
        buy  = piz.get("compra")
        sell = piz.get("venta")
        name = b.get("nombre") or BANCOS_NOMBRE.get(bid, bid)
        banks_data.append({
            "name": str(name).strip(),
            "buy":  round(float(buy),  2) if buy  is not None and float(buy)  > 0 else None,
            "sell": round(float(sell), 2) if sell is not None and float(sell) > 0 else None,
        })
    banks_data.sort(key=lambda x: x["buy"] or 0, reverse=True)
    print(f"   {len(banks_data)} bancos obtenidos de la API")
    for b in banks_data:
        print(f"   {b['name']}: Compra {b['buy']} | Venta {b['sell']}")
else:
    print("   Bancos no disponibles — usando datos estáticos")
    banks_data = [
        {"name": "Banco FIE",            "buy": 11.50, "sell": 12.00},
        {"name": "BCP",                  "buy": 11.50, "sell": 12.30},
        {"name": "BNB",                  "buy": 11.50, "sell": 12.30},
        {"name": "Banco Bisa",           "buy": 11.30, "sell": 12.30},
        {"name": "Banco Económico",      "buy": 11.30, "sell": 12.35},
        {"name": "Banco Unión",          "buy": 11.00, "sell": 12.30},
        {"name": "Mercantil Santa Cruz", "buy": 10.90, "sell": 12.30},
        {"name": "BancoSol",             "buy": 10.80, "sell": 12.30},
        {"name": "Banco Ganadero",       "buy": None,  "sell": 12.30},
    ]

# ── BCB Oficial ────────────────────────────────────────────────────────────
print("\n3. BCB Oficial...")
if d_official and d_official.get("official"):
    off = d_official["official"]
    blue = d_official.get("blue", {})
    bcb_data = {
        "officialBuy":     off["buy"],
        "officialSell":    off["sell"],
        "referentialBuy":  blue.get("buy",  buy_price),
        "referentialSell": blue.get("sell", sell_price),
        "vrdBuy":  float(d_bcb_vrd["buy"])  if d_bcb_vrd and d_bcb_vrd.get("buy")  else 9.79,
        "vrdSell": float(d_bcb_vrd["sell"]) if d_bcb_vrd and d_bcb_vrd.get("sell") else 10.0,
    }
else:
    bcb_data = existing.get("bcb", {
        "officialBuy": 6.86, "officialSell": 6.96,
        "referentialBuy": 9.86, "referentialSell": 10.07
    })
    # Actualizar VRD si está disponible aunque officialRate haya fallado
    if d_bcb_vrd and d_bcb_vrd.get("buy"):
        bcb_data["vrdBuy"]  = float(d_bcb_vrd["buy"])
        bcb_data["vrdSell"] = float(d_bcb_vrd["sell"])
print(f"   Oficial  Compra: {bcb_data['officialBuy']} | Venta: {bcb_data['officialSell']}")

# ── BCB VRD ────────────────────────────────────────────────────────────────
print("\n4. BCB VRD...")
vrd_data    = load_json("data/bcb_vrd.json")
vrd_history = vrd_data.get("history", [])

# Primero intenta la API de DolarBlueBolivia (ya tiene el scraping hecho)
vrd_today = None
if d_bcb_vrd and d_bcb_vrd.get("buy"):
    vrd_today = float(d_bcb_vrd["buy"])
    print(f"   BCB VRD (via DolarBlue API): {vrd_today}")
else:
    # Fallback: scraping directo de bcb.gob.bo
    vrd_today = fetch_bcb_vrd_direct()
    if vrd_today:
        print(f"   BCB VRD (scraping directo): {vrd_today}")

vrd_sell_today = float(d_bcb_vrd["sell"]) if d_bcb_vrd and d_bcb_vrd.get("sell") else None

if vrd_today:
    vrd_history = [h for h in vrd_history if h["date"] != today_str]
    # Preservar min/max/n_trans si ya existen para hoy
    prev_today = next((h for h in vrd_data.get("history", []) if h["date"] == today_str), {})
    vrd_history.append({
        "date": today_str,
        "vrd": vrd_today,
        "min":     prev_today.get("min"),
        "max":     prev_today.get("max") or vrd_sell_today,
        "monto":   prev_today.get("monto", 0),
        "n_trans": prev_today.get("n_trans", 0),
    })
    vrd_history = sorted(vrd_history, key=lambda x: x["date"])
else:
    print("   BCB VRD no disponible -> usando dato guardado")
    vrd_today = vrd_data.get("vrd_today", 9.86)

# ── Noticias Económicas Bolivia (RSS) ─────────────────────────────────────
print("\n5. Noticias económicas (RSS)...")

NEWS_KEYWORDS = [
    "dólar","dolar","tipo de cambio","boliviano","banco central","bcb",
    "reservas","inflación","inflacion","economía","economia",
    "diésel","diesel","combustible","exportaciones","importaciones",
    "deuda","fiscal","tco","moneda","divisa","finanzas",
    "presupuesto","gas","litio","inversión","inversion","crecimiento",
]

RSS_SOURCES = [
    {"name": "Los Tiempos",  "url": "https://www.lostiempos.com/rss.xml"},
    {"name": "Página Siete", "url": "https://www.paginasiete.bo/rss"},
    {"name": "El Deber",     "url": "https://eldeber.com.bo/rss.xml"},
    {"name": "Urgente Bo",   "url": "https://urgente.bo/feed"},
]

def strip_html(txt):
    return re.sub(r"<[^>]+>", "", txt or "").strip()

def rss_date_to_iso(raw):
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
    return None

def fetch_rss(source, max_items=6):
    h = {"User-Agent": HEADERS["User-Agent"], "Accept": "application/rss+xml, application/xml, text/xml"}
    req = urllib.request.Request(source["url"], headers=h)
    items = []
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
        root = ET.fromstring(raw)
        channel = root.find("channel") or root
        for item in channel.findall("item")[:20]:
            title = strip_html(item.findtext("title") or "")
            desc  = strip_html(item.findtext("description") or "")
            link  = (item.findtext("link") or "").strip()
            pub   = item.findtext("pubDate") or ""
            text  = (title + " " + desc).lower()
            if not any(kw in text for kw in NEWS_KEYWORDS):
                continue
            items.append({
                "source": source["name"],
                "title":  title,
                "desc":   desc[:200] + ("…" if len(desc) > 200 else ""),
                "link":   link,
                "date":   rss_date_to_iso(pub) or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            if len(items) >= max_items:
                break
    except Exception as e:
        print(f"   RSS error {source['name']}: {e}")
    return items

all_news = []
for src in RSS_SOURCES:
    items = fetch_rss(src)
    all_news.extend(items)
    print(f"   {src['name']}: {len(items)} noticias")

all_news.sort(key=lambda x: x["date"], reverse=True)
all_news = all_news[:15]
print(f"   Total: {len(all_news)} noticias seleccionadas")

# ── Predicción de tendencia ────────────────────────────────────────────────
print("\n6. Calculando predicción...")

def calc_prediction(history_list, current_buy, current_sell):
    recent = sorted(history_list, key=lambda x: x["date"])[-7:]
    if len(recent) < 3:
        return None
    buys  = [float(h["buy"])  for h in recent]
    sells = [float(h["sell"]) for h in recent]
    n = len(buys)
    xs = list(range(n))
    def linreg(ys):
        xm = sum(xs)/n; ym = sum(ys)/n
        num = sum((xs[i]-xm)*(ys[i]-ym) for i in range(n))
        den = sum((xs[i]-xm)**2 for i in range(n))
        slope = num/den if den else 0
        return slope, ym - slope*xm
    sb, ib = linreg(buys)
    ss, is_ = linreg(sells)
    pb = max(round(sb*(n)+ib, 2), 0.01)
    ps = max(round(ss*(n)+is_, 2), 0.01)
    change_b = round(pb - current_buy,  2)
    change_s = round(ps - current_sell, 2)
    avg_change = (abs(change_b)+abs(change_s))/2
    trend = "estable" if avg_change < 0.01 else ("alza" if (change_b+change_s) > 0 else "baja")
    return {
        "buyTomorrow":  pb, "sellTomorrow": ps,
        "changeBuy":    change_b, "changeSell": change_s,
        "trend":        trend,
        "confidence":   "alta" if len(recent) >= 6 else "media",
        "basedOnDays":  len(recent),
    }

hist_for_pred = existing.get("history", [])
hist_for_pred = [h for h in hist_for_pred if h["date"] != today_str]
hist_for_pred.append({"date": today_str, "buy": buy_price, "sell": sell_price})
prediction = calc_prediction(hist_for_pred, buy_price, sell_price)
if prediction:
    print(f"   Mañana estimado — Compra: {prediction['buyTomorrow']} | Venta: {prediction['sellTomorrow']} | Tendencia: {prediction['trend']}")
else:
    print("   Sin suficientes datos")

# ── Historial USDT ─────────────────────────────────────────────────────────
history = existing.get("history", [])
history = [h for h in history if h["date"] != today_str]
history.append({"date": today_str, "buy": buy_price, "sell": sell_price})
history = sorted(history, key=lambda x: x["date"])

# ── Guardar ────────────────────────────────────────────────────────────────
save_json("data/prices.json", {
    "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "displayDate": display_date,
    "binance":  {"buy": buy_price,  "sell": sell_price, "available": True, "source": "binance_p2p"},
    "eldorado": eldorado_data,
    "takenos":  takenos_data,
    "wallbit":  wallbit_data,
    "airtm":    airtm_data,
    "bybit":    bybit_data,
    "saldoar":  saldoar_data,
    "bcb":      bcb_data,
    "banks":    banks_data,
    "news":       all_news,
    "prediction": prediction,
    "history":    history,
})
print("\nprices.json guardado.")

today_entry = next((h for h in vrd_history if h["date"] == today_str), {})
save_json("data/bcb_vrd.json", {
    "lastUpdated":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "today":          today_str,
    "vrd_today":      vrd_today,
    "vrd_sell_today": vrd_sell_today,
    "vrd_min_today":  today_entry.get("min"),
    "vrd_max_today":  today_entry.get("max") or vrd_sell_today,
    "n_trans_today":  today_entry.get("n_trans") or None,
    "history":        vrd_history,
})
print("bcb_vrd.json guardado.")

print("\n=== RESUMEN ===")
print(f"  Binance P2P : Compra {buy_price}  | Venta {sell_price}")
print(f"  El Dorado   : Compra {eldorado_data['buy']} | Venta {eldorado_data['sell']}  [{eldorado_data['source']}]")
print(f"  Takenos     : Compra {takenos_data['buy']} | Venta {takenos_data['sell']}  [{takenos_data['source']}]")
print(f"  Wallbit     : Compra {wallbit_data['buy']} | Venta {wallbit_data['sell']}  [{wallbit_data['source']}]")
print(f"  AirTM       : Compra {airtm_data['buy']} | Venta {airtm_data['sell']}  [{airtm_data['source']}]")
print(f"  Bybit P2P   : Compra {bybit_data['buy']} | Venta {bybit_data['sell']}  [{bybit_data['source']}]")
print(f"  SaldoAr     : Compra {saldoar_data['buy']} | Venta {saldoar_data['sell']}  [{saldoar_data['source']}]")
print(f"  BCB Oficial : Compra {bcb_data['officialBuy']} | Venta {bcb_data['officialSell']}")
print(f"  BCB VRD     : {vrd_today}")
