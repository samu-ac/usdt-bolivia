import csv
import json
from datetime import datetime
from collections import defaultdict

INPUT = r"C:\Users\Samuel A\Downloads\DATABASE DOLAR BLUE EN BOLIVIA - Hoja1.csv"
OUTPUT = r"C:\Users\Samuel A\Fundamentos USDT - BOL\data\prices.json"

daily = defaultdict(lambda: {"buy": [], "sell": [], "bcb_buy": [], "bcb_sell": []})

with open(INPUT, encoding="utf-8", errors="ignore") as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) < 5:
            continue
        try:
            dt_str = row[0].strip()
            # Handle D/MM/YYYY or DD/MM/YYYY
            dt = datetime.strptime(dt_str, "%d/%m/%Y %H:%M:%S")
            date_key = dt.strftime("%Y-%m-%d")

            bcb_buy  = float(row[1].strip().replace(",", "."))
            bcb_sell = float(row[2].strip().replace(",", "."))
            p2p_buy  = float(row[3].strip().replace(",", "."))
            p2p_sell = float(row[4].strip().replace(",", "."))

            daily[date_key]["buy"].append(p2p_buy)
            daily[date_key]["sell"].append(p2p_sell)
            daily[date_key]["bcb_buy"].append(bcb_buy)
            daily[date_key]["bcb_sell"].append(bcb_sell)
        except Exception:
            continue

def avg(lst):
    return round(sum(lst) / len(lst), 2) if lst else None

history = []
for date in sorted(daily.keys()):
    d = daily[date]
    history.append({
        "date": date,
        "buy":  avg(d["buy"]),
        "sell": avg(d["sell"])
    })

# Last day values
last = history[-1] if history else {}
last_bcb = daily[sorted(daily.keys())[-1]]

# Keep existing JSON structure and merge
try:
    with open(OUTPUT, encoding="utf-8") as f:
        existing = json.load(f)
except Exception:
    existing = {}

# Display date in Spanish
DAYS_ES   = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
MONTHS_ES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
now = datetime.now()
display_date = f"{DAYS_ES[now.weekday()]} {now.day} de {MONTHS_ES[now.month-1]}, {now.year}"

buy_today  = last.get("buy",  existing.get("binance", {}).get("buy",  9.93))
sell_today = last.get("sell", existing.get("binance", {}).get("sell", 9.96))

bcb_buy_today  = avg(last_bcb["bcb_buy"])  or 6.86
bcb_sell_today = avg(last_bcb["bcb_sell"]) or 6.96

output = {
    "lastUpdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "displayDate": display_date,
    "binance":  {"buy": buy_today,  "sell": sell_today,  "available": True},
    "airtm":    {"buy": round(buy_today * 0.996, 2), "sell": round(sell_today * 0.997, 2), "available": True},
    "eldorado": {"buy": round(buy_today * 0.993, 2), "sell": round(sell_today * 0.994, 2), "available": True},
    "takenos":  {"buy": round(buy_today * 0.990, 2), "sell": round(sell_today * 0.991, 2), "available": True},
    "bcb": {
        "officialBuy":    bcb_buy_today,
        "officialSell":   bcb_sell_today,
        "referentialBuy": buy_today,
        "referentialSell": sell_today
    },
    "history": history
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"OK - {len(history)} dias procesados")
print(f"   Rango: {history[0]['date']} - {history[-1]['date']}")
print(f"   Hoy: Compra {buy_today} | Venta {sell_today}")
