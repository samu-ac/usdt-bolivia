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
| `bcb.officialBuy/Sell` | Tipo oficial BCB USD | Referencia oficial |
| `bcb.referentialSell`  | Referencial mercado, sell | Lo que el usuario paga |
| `bcb.referentialBuy`   | Referencial mercado, buy  | Lo que el usuario recibe |

---

## Convención de datos (crítico)

| Proveedor | Convención | `buy` | `sell` |
|---|---|---|---|
| **Binance** | Market-centric | 11.82 (lo que el mercado paga = usuario RECIBE) | 11.88 (lo que el mercado vende = usuario PAGA) |
| **Eldorado, Takenos, Wallbit, AirTM, Bybit, SaldoAr** | User-centric | Mayor (~12.09) — usuario PAGA | Menor (~11.58) — usuario RECIBE |
| **history[]** | Market-centric (igual a Binance) | `buy < sell` siempre | — |

**Regla de display:**
- Binance → mostrar `sell` en "Tú compras", `buy` en "Tú vendes"  
- Todos los demás → mostrar `buy` en "Tú compras", `sell` en "Tú vendes" (sin swap)

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

---

## Pendientes / Bloqueados (requieren decisión o verificación externa)

| Item | Descripción | Estado |
|---|---|---|
| F — Restricciones bancarias | Fecha 21/04/2026, etiqueta "Sin restricciones" con límites mensuales, "Por confirmar" | Requiere verificación manual en webs oficiales de cada banco |
| G — Links bancarios | Algunos links pueden apuntar solo al home del banco, no al tarifario | Verificación manual por banco |
| H — Footer links `#` | Links "Fuentes de Datos" y "Blog" con anchors vacíos | Requiere crear páginas destino |
| I — Indicador "En vivo" con datos potencialmente desactualizados | El badge "En vivo" no valida antigüedad del timestamp | Requiere lógica de stale-check basada en `lastUpdated` |
| J — `calcRatePill` siempre muestra `binance.sell` | Cuando modo es USDT→BOB, la tasa usada es `binance.buy` (11.82) pero pill muestra 11.88 | Inconsistencia menor en la UI del widget calculadora |

---

## Validaciones ejecutadas

- ✅ Revisión estática del código: contratos de precios verificados en `fetch_prices.py`, `prices.json`, `index.html`
- ✅ Convención data verificada proveedor por proveedor contra `prices.json` real
- ✅ Test case calculadora: sell 100 USDT = Bs 1182 (binance.buy=11.82) ✓; buy USDT con Bs 1188 = 100 USDT (1/binance.sell=1/11.88) ✓
- ✅ Spread con datos reales: Binance (11.88-11.82)/11.82×100 = 0.51%; Takenos (12.11-11.71)/11.71×100 = 3.42% ✓
- ✅ Modales privacidad/términos corregidos a "USDT Bolivia"
- ⚠️ No ejecutado en navegador (sin servidor local disponible en esta sesión)
- ⚠️ `calculadora-usdt-bolivianos.html` — no auditada en esta fase (fue corregida en sesión anterior)

---

## Próximo paso: Fase 2 — Revisión visual y pendientes

- Verificar en navegador que la tabla comparadora muestra Compra > Venta en todas las filas
- Verificar gráfico con etiquetas "Tú compras" / "Tú vendes" correctas
- Revisar sección de restricciones bancarias con datos verificados
- Crear página de metodología y fuentes
- Implementar stale-check para badge "En vivo"
- Corregir `calcRatePill` para mostrar la tasa correcta según dirección
