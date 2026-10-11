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

## Hallazgos confirmados y correcciones aplicadas

| # | Síntoma | Causa | Corrección | Archivo |
|---|---|---|---|---|
| 1 | Tabla comparador mostraba Compra < Venta (buy=11.82 en columna "Compra") | `renderExchanges()` usaba `d.binance.buy` como precio de compra del usuario | Swap: `uBuy = d.binance.sell`, `uSell = d.binance.buy` | index.html:1552 |
| 2 | Spread `--0.51%` (doble negativo) | `p.buy < p.sell` por el bug #1, daba spread negativo, template `-${spread}%` lo duplicaba | Fórmula corregida: `(p.buy - p.sell) / p.sell * 100`; eliminado prefijo `-` del template | index.html:1589 |
| 3 | Gráfico etiqueta "VENTA Bs 11.88" siendo que 11.88 es precio de compra | Dataset `h.sell` (market's sell = user buy) llamado `'Venta'` | Renombrados a `'Tú compras'` / `'Tú vendes'`; stat "VENTA" renombrado a "TÚ COMPRAS" | index.html:2038 |
| 4 | Tarjetas de plataforma "Tú compras" mostraba 11.82 (precio de venta) | `platCard()` usaba `data.buy` = market's buy = user's sell | Swap: `userBuy = data.sell`, `userSell = data.buy` | index.html:1391 |
| 5 | Calculadora mini: USDT→BOB usaba `binance.sell` en lugar de `binance.buy` | Precio de venta del usuario requiere `binance.buy` (menor) | Corregido a `binance.buy` para la dirección USDT→BOB | index.html:2073 |
| 6 | Texto hardcodeado "BCB (Bs 6.96)" — valor histórico caducado | Literal estático anterior al acuerdo FMI (tasa actual ~11.73) | Reemplazado con `pricesData.bcb.officialBuy` dinámico | index.html:1830 |
| 7 | Nota "TCO BCB (Bs 12)" hardcodeada | Valor estático | Reemplazado con texto descriptivo sin cifra hardcodeada | index.html:784 |
| 8 | Subtítulo gráfico "~Bs 11.97" hardcodeado | Valor de referencia antiguo | Eliminada cifra estática | index.html:792 |
| 9 | Proyección texto "14 días" pero código usa 7 días | Discrepancia texto/código | Corregido a "7 días" | index.html:1833 |
| 10 | "★★★★★ 5.0 · Partner Verificado" sin metodología | Sin evidencia de ratings ni alianzas documentadas | Eliminadas etiquetas; reemplazadas por primera feature de la plataforma | index.html:1396,1440 |
| 11 | Claim "0% comisión" Binance P2P | Binance P2P tiene fees maker/taker según montos | Reemplazado con descripción neutra | index.html:900 |

---

## Pendientes / Bloqueados (requieren decisión o verificación externa)

| Item | Descripción | Bloqueo |
|---|---|---|
| F — Restricciones bancarias | Fecha 21/04/2026, etiqueta "Sin restricciones" con límites mensuales, "Por confirmar" | Requiere verificación manual en webs oficiales de cada banco |
| G — Links bancarios | Algunos links pueden apuntar solo al home del banco, no al tarifario | Verificación manual por banco |
| H — Política de privacidad | Modal de privacidad menciona "Dólar Bolivia" en lugar de "USDT Bolivia" | Corrección de texto pendiente (no afecta funcionalidad) |
| H — Footer links `#` | Links "Fuentes de Datos" y "Blog" con anchors vacíos | Requiere crear páginas destino |
| I — Horario "12:14 a. m. p.m." | No encontrado en código en esta auditoría | Sin reproducir — posible texto generado dinámico |

---

## Validaciones ejecutadas

- ✅ Revisión estática del código: contratos de precios verificados en `fetch_prices.py`, `prices.json`, `index.html`, `calculadora-usdt-bolivianos.html`
- ✅ Cálculo manual del spread con datos reales (11.88, 11.82): formula corregida da +0.51% ✓
- ✅ Verificación de la predicción: `calc_prediction()` en `fetch_prices.py` usa `[-7:]` — texto actualizado a 7 días
- ⚠️ No ejecutado en navegador (sin servidor local disponible en esta sesión)
- ⚠️ `calculadora-usdt-bolivianos.html` — no auditada en esta fase (fue corregida en sesión anterior)

---

## Próximo paso: Fase 2 — Revisión visual

- Verificar en navegador que la tabla comparadora muestra Compra (11.88) > Venta (11.82)
- Verificar gráfico con etiquetas correctas
- Revisar sección de restricciones bancarias con datos reales verificados
- Crear página de metodología y fuentes
- Revisar modal de privacidad (texto "Dólar Bolivia")
