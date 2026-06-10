"""
Procesa el CSV del VRD (Valor Referencial de Compra) del BCB.
Calcula promedio ponderado diario: sum(TC * Monto) / sum(Monto)
Genera data/bcb_vrd.json con historial + metadata
"""
import csv, json, os
from datetime import datetime
from collections import defaultdict

INPUT  = r"C:\Users\Samuel A\Downloads\vrd_compra_2026-04-30_al_2026-06-09.csv"
OUTPUT = r"C:\Users\Samuel A\Fundamentos USDT - BOL\data\bcb_vrd.json"

# Estructura: {fecha: {tc_weighted_sum, total_monto, min_tc, max_tc, n_trans}}
daily = defaultdict(lambda: {"w_sum": 0.0, "monto": 0.0, "min_tc": 9999, "max_tc": 0, "n": 0})

with open(INPUT, encoding="utf-8-sig", errors="ignore") as f:
    reader = csv.reader(f, delimiter=";")
    for i, row in enumerate(reader):
        if i < 8: continue           # saltear cabeceras
        if len(row) < 4: continue
        if not row[0].strip(): continue

        try:
            fecha_str = row[0].strip()
            dt = datetime.strptime(fecha_str, "%d/%m/%Y")
            date_key = dt.strftime("%Y-%m-%d")
            tc = float(row[1].strip().replace(",", "."))
        except Exception:
            continue

        # Sumar montos de todos los bancos (columnas impares desde col 3)
        monto_fila = 0.0
        n_fila = 0
        for j in range(2, len(row), 2):
            try:
                n_val = row[j].strip()
                m_val = row[j+1].strip() if j+1 < len(row) else "-"
                if n_val not in ("-", "", None) and m_val not in ("-", "", None):
                    n_fila += int(n_val)
                    monto_fila += float(m_val.replace(",", "."))
            except Exception:
                continue

        if monto_fila <= 0:
            continue

        d = daily[date_key]
        d["w_sum"]  += tc * monto_fila
        d["monto"]  += monto_fila
        d["n"]      += n_fila
        d["min_tc"]  = min(d["min_tc"], tc)
        d["max_tc"]  = max(d["max_tc"], tc)

history = []
for date in sorted(daily.keys()):
    d = daily[date]
    if d["monto"] > 0:
        vrd = round(d["w_sum"] / d["monto"], 4)
        history.append({
            "date":   date,
            "vrd":    vrd,
            "min":    round(d["min_tc"], 4),
            "max":    round(d["max_tc"], 4),
            "monto":  round(d["monto"], 2),
            "n_trans": d["n"]
        })

last = history[-1] if history else {}
now  = datetime.utcnow()

output = {
    "lastUpdated":   now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "today":         last.get("date", ""),
    "vrd_today":     last.get("vrd", 9.86),
    "vrd_min_today": last.get("min", 9.70),
    "vrd_max_today": last.get("max", 9.99),
    "monto_today":   last.get("monto", 0),
    "n_trans_today": last.get("n_trans", 0),
    "history":       history
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"OK - {len(history)} dias procesados")
print(f"   Rango: {history[0]['date']} -> {history[-1]['date']}")
print(f"   VRD hoy: {last.get('vrd')} Bs/USD  (n={last.get('n_trans')} transacciones, Monto=${last.get('monto'):,.0f})")
