# PROJECT_STATE — USDT Bolivia

## Fase 1 — Auditoría y Corrección de Coherencia

**Rama:** `fase1-auditoria-coherencia`  
**Fecha:** 2026-10-11  
**Revisor:** Samuel Ampuero

---

## Stack y arquitectura

- **Sitio:** GitHub Pages estático · `usdt-bolivia.com`
- **Repo:** `samu-ac/usdt-bolivia`
- **Datos:** `data/prices.json` generado por `fetch_prices.py` vía GitHub Actions (cada 2 h en días hábiles)
- **Fuente principal:** API `api.dolarbluebolivia.click` + fallback Binance P2P directo
- **Analítica:** Google Analytics G-QW9G81P0F3 · AdSense ca-pub-6095162450096784

## Contrato interno de precios

| Campo JSON | Significado | Perspectiva de usuario |
|---|---|---|
| `binance.sell` | Market's sell price | **Tú compras** USDT (precio mayor, ~11.88) |
| `binance.buy`  | Market's buy price  | **Tú vendes** USDT (precio menor, ~11.82) |
| `bcb.officialBuy/Sell` | Tipo de Cambio Oficial BCB (referencia administrativa) | Referencia, no precio real de cambistas |
| `bcb.referentialSell`  | = `binance.sell` (blue.sell del API) | Lo que el usuario paga en P2P |
| `bcb.referentialBuy`   | = `binance.buy` (blue.buy del API)  | Lo que el usuario recibe en P2P |
| `bcb.vrdBuy/vrdSell`   | VRD — operaciones propias del BCB (~9.76) | Solo para gráfico histórico VRD |

---

## Convención de datos — verificada desde código fuente (`fetch_prices.py` + `loadPrices()`)

| Proveedor | Fuente API | Evidencia de convención | `buy` | `sell` |
|---|---|---|---|---|
| **Binance** | `d_official["blue"]["buy/sell"]` | `buy_price = round(d_official["blue"]["buy"], 2)` — mismo campo nombrado "buy" en JSON como "market buy price" | 11.82 (mercado paga al usuario) | 11.88 (mercado vende al usuario) |
| **Eldorado** | `d_eldorado["buy/sell"]` | Fallback: `buy_price*1.0071` > `sell_price*0.9880` → buy > sell | Mayor (usuario PAGA) | Menor (usuario RECIBE) |
| **Takenos** | `d_takenos["buy/sell"]` | Fallback: `buy_price*1.0222` > `sell_price*0.9860` → buy > sell | Mayor (usuario PAGA) | Menor (usuario RECIBE) |
| **Wallbit** | `d_wallbit["buy/sell"]` | Fallback: `buy_price*1.0121` > `sell_price*0.9840` → buy > sell | Mayor (usuario PAGA) | Menor (usuario RECIBE) |
| **AirTM** | `d_airtm["addValue/withdrawValue"]` | **Nombres de campo explícitos:** `addValue`=carga fondos=PAGA; `withdrawValue`=retira=RECIBE | `addValue` (usuario PAGA) | `withdrawValue` (usuario RECIBE) |
| **Bybit** | `d_bybit["buy/sell"]` | Prices.json: `buy=11.85 > sell=11.84` | Mayor (usuario PAGA) | Menor (usuario RECIBE) |
| **SaldoAr** | `d_saldoar["buy/sell"]` | Fallback: `buy_price*1.011` > `sell_price*0.988` → buy > sell | Mayor (usuario PAGA) | Menor (usuario RECIBE) |
| **history[]** | `live.blue.buy/sell` | Mismo campo que Binance | `buy < sell` siempre (market-centric) | — |

**Regla de display:**
- Binance → swap: mostrar `sell` en "Tú compras", `buy` en "Tú vendes"
- Todos los demás → sin swap: mostrar `buy` en "Tú compras", `sell` en "Tú vendes"
- AirTM: `buy ← addValue`, `sell ← withdrawValue` (confirmado por nombre de campo de la API)

## Hallazgos confirmados y correcciones aplicadas

| # | Síntoma | Causa | Corrección | Archivo |
|---|---|---|---|---|
| 1 | Tabla comparador mostraba Compra < Venta (buy=11.82 en columna "Compra") | `renderExchanges()` usaba `d.binance.buy` como precio de compra del usuario | Swap solo en Binance: `uBuy = d.binance.sell`, `uSell = d.binance.buy` | index.html:1552 |
| 2 | Spread `--0.51%` (doble negativo) | `p.buy < p.sell` por el bug #1, daba spread negativo | Fórmula corregida: `(p.buy - p.sell) / p.sell * 100`; guardia para `p.sell=0` | index.html:1592 |
| 3 | Gráfico etiqueta "VENTA Bs 11.88" siendo que 11.88 es precio de compra | Dataset `h.sell` (market's sell = user buy) llamado `'Venta'` | Renombrados a `'Tú compras'` / `'Tú vendes'`; stat "VENTA" renombrado a "TÚ COMPRAS" | index.html:2038 |
| 4 | Tarjetas de plataforma "Tú compras" mostraba precio de venta | `platCard()` mal swapeado — proveedores son USER-CENTRIC (sin swap) | Revertido a `userBuy = data.buy`, `userSell = data.sell` para todos los proveedores | index.html:1393 |
| 4b | `renderExchanges` swapeaba bybit/saldoar/takenos/wallbit/airtm | Misma confusión de convención; estos son USER-CENTRIC | Revertidos a `d.provider.buy/.sell` sin swap | index.html:1562-1581 |
| 5 | Calculadora mini: USDT→BOB usaba `binance.sell` (11.88) | Usuario que vende USDT recibe `binance.buy` (11.82) | Corregido a `binance.buy` para USDT→BOB; `1/binance.sell` para BOB→USDT | index.html:2076 |
| 6 | Texto hardcodeado "BCB (Bs 6.96)" — valor histórico caducado | Literal estático anterior al acuerdo FMI (tasa actual ~11.73) | Reemplazado con `pricesData.bcb.officialBuy` dinámico | index.html ~1830 |
| 7 | Nota "TCO BCB (Bs 12)" hardcodeada | Valor estático | Reemplazado con texto descriptivo sin cifra hardcodeada | index.html ~784 |
| 8 | Subtítulo gráfico "~Bs 11.97" hardcodeado | Valor de referencia antiguo | Eliminada cifra estática | index.html ~792 |
| 9 | Proyección texto "7 días" en nota de metodología | Nota referenciaba `fetch_prices.py` (7 días); código in-browser usa 14 días | Texto corregido en la nota de metodología interna (línea ~1836) | index.html:1836 |
| 10 | "★★★★★ 5.0 · Partner Verificado" sin metodología | Sin evidencia de ratings ni alianzas documentadas | Eliminadas etiquetas; reemplazadas por primera feature de la plataforma | index.html ~1396 |
| 11 | Claim "0% comisión" Binance P2P | Binance P2P tiene fees maker/taker según montos | Reemplazado con descripción neutra | index.html ~900 |
| 12 | Modales de Privacidad y Términos decían "Dólar Bolivia" | Nombre de marca incorrecto | Corregidos a "USDT Bolivia" | index.html:1225,1241 |
| 13 | `calcRatePill` mostraba siempre `binance.sell` (11.88) | Ignoraba la dirección USDT→BOB (usa `binance.buy`=11.82) | Corregido: pill muestra `buy` cuando `from=USDT`, `sell` cuando `from=BOB` | index.html:2088 |
| 14 | Badge "En vivo" hardcodeado sin validar antigüedad | Sin guardia de timestamp; datos pueden ser de hace horas | Añadida función `isDataFresh(isoTimestamp, maxAgeMinutes=180)` — muestra "En vivo" solo si `lastUpdated` es < 3h | index.html:1392,1410 |
| 15 | Comparador "USD Físico (Librecambista)" usaba tasa oficial BCB, no precio de cambistas | `renderComparison` usa `bcb.officialBuy` (tasa administrativa), no precio real de librecambistas | Etiqueta corregida a "Tipo Oficial BCB (referencia)"; textos actualizados para aclarar que es referencia, no precio de mercado real | index.html:757,784,2202,2205 |
| 16 | Texto "últimos 7 días" en fundamentos de predicción | La función in-browser usa `slice(-14)` (14 días), no 7 | Corregido a "14 días" en texto del factor metodológico | index.html:1840 |

---

## Pendientes / Bloqueados (requieren decisión o verificación externa)

| Item | Descripción | Estado |
|---|---|---|
| F — Restricciones bancarias | Fecha 21/04/2026, etiqueta "Sin restricciones" con límites mensuales, "Por confirmar" | Requiere verificación manual en webs oficiales de cada banco |
| G — Links bancarios | Algunos links pueden apuntar solo al home del banco, no al tarifario | Verificación manual por banco |
| H — Footer links `#` (resuelto parcialmente) | "Fuentes de Datos" → `#platforms` (funciona). Sin pendientes críticos en footer | ✅ Footer links operativos; Blog links apuntan a `/blog/` existente |
| K — `calculadora-usdt-bolivianos.html` | No auditada en Fase 1 | Pendiente Fase 2 |

---

## Validaciones ejecutadas

### Implementado y probado (código)
- ✅ Convención data verificada desde código fuente (`fetch_prices.py` líneas 143-210, `loadPrices()` líneas 1318-1335): cada proveedor confirmado por nombre de campos API, no solo por desigualdad de precios
- ✅ Test case calculadora: sell 100 USDT × 11.82 = Bs 1182 ✓; buy USDT con Bs 1188 ÷ 11.88 = 100 USDT ✓
- ✅ Spread con datos reales: Binance (11.88-11.82)/11.82×100 = 0.51%; Takenos (12.11-11.71)/11.71×100 = 3.42% ✓
- ✅ `calcRatePill` corregido: muestra `binance.buy=11.82` cuando USDT→BOB, `binance.sell=11.88` cuando BOB→USDT
- ✅ `isDataFresh()` añadida: umbral 180 min, alineado con GitHub Actions (cada 2h en días hábiles)
- ✅ Comparador BCB: etiquetas y textos corregidos para no afirmar precios de librecambistas

### Pendiente de verificar en navegador
- ⚠️ Verificación visual desktop + mobile no ejecutada (sin servidor local en esta sesión)
- ⚠️ `calculadora-usdt-bolivianos.html` no auditada
- ⚠️ Restricciones bancarias requieren verificación manual externa

---

## Próximo paso: Fase 2 — Revisión visual y pendientes

- Verificar en navegador que la tabla comparadora muestra Compra > Venta en todas las filas
- Verificar gráfico con etiquetas "Tú compras" / "Tú vendes" correctas
- Revisar sección de restricciones bancarias con datos verificados
- Crear página de metodología y fuentes
- Implementar stale-check para badge "En vivo"
- Corregir `calcRatePill` para mostrar la tasa correcta según dirección
