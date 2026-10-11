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

| # | Síntoma | Causa | Corrección | Archivo |
|---|---|---|---|---|
| 17 | `source` undefined en todos los proveedores después de `loadPrices()` | La actualización en vivo sobreescribía el objeto sin incluir `source` | Asignados identificadores exactos de `fetch_prices.py` (`'binance_p2p'`, `'api_dbb_eldorado'`, etc.) en `loadPrices()` | index.html:1319-1335 |
| 17b | `source: 'live'` genérico no distinguía `api_dbb_*` de `calculated` — podía etiquetar un estimado como "En vivo" | `loadPrices()` asignaba `source: 'live'` uniforme sin verificar procedencia | Reemplazado por identificadores específicos por proveedor (mismo esquema que `fetch_prices.py`) | index.html:1319-1335 |
| 17c | `lastUpdated` no se actualizaba tras refresh exitoso del browser | `loadPrices()` conservaba el `lastUpdated` del JSON aunque los precios fueran recién obtenidos | Añadido `base.lastUpdated = new Date().toISOString()` dentro del bloque try tras actualizaciones exitosas | index.html:~1362 |
| 18 | Badge "En vivo" sin distinción de procedencia | `platCard()` usaba `isDataFresh(lastUpdated)` global sin verificar que el source fuera observado | Añadida `isObservedSource(src)` (true si `api_dbb_*` o `binance_p2p`); badge: "Estimado" si calculated, "En vivo" si observed+fresco, "Referencial" si no | index.html:1393,1420 |
| 19 | Tarjetas bancarias "Sin restricciones" con límites mensuales visibles | Badge contradecía el monto mensual documentado | Cambiados todos los `data-status="ok"` y badge `ok` a `data-status="mod"` y badge "Con límite mensual"; Fortaleza → "Por confirmar" | index.html:1003-1062 |
| 20 | Texto predicción "14 días" incorrecto (span 19 días calendario) | `slice(-14)` da 14 registros de días hábiles, no 14 días corridos | Texto aclarado: "últimos 14 registros históricos … días hábiles registrados, no necesariamente 14 días calendario" | index.html:1840 |
| 21 | Bug C1 en `calculadora-usdt-bolivianos.html`: swap no recalcula | `swapInputs()` intercambiaba valores pero no llamaba `calcFromTop()` | Añadida llamada a `calcFromTop()` al final de `swapInputs()` | **calculadora-usdt-bolivianos.html**:261 |
| 22 | Bug C2 en `calculadora-usdt-bolivianos.html`: etiquetas no cambian con modo | `setMode()` actualizaba tabs pero no `labelTop`/`labelBottom` | Añadidas actualizaciones de etiquetas según modo (comprar/vender) | **calculadora-usdt-bolivianos.html**:227 |
| 23 | Bug C3 en `calculadora-usdt-bolivianos.html`: `calcBob()` usaba `buyRate` | BOB→USDT requiere pagar el precio de compra (`sellRate`=11.88), no `buyRate`=11.82 | Cambiado a `usdt = bob / sellRate` | **calculadora-usdt-bolivianos.html**:296 |
| 24 | `renderExchanges()` hardcodeaba "Live" por nombre de proveedor | Lista de strings `p.name === 'Bybit P2P' \|\| ...` no refleja source real | Badge derivado de `isObservedSource(p.source) && fresh`; OKX/Bitget/Vita/BCP/CriptoBISA muestran "Ref." | index.html:~1600 |
| 25 | Bybit y AirTM sin caveat de convención en UI | Convención buy/sell de Bybit no verificada independientemente; AirTM — asset no confirmado (¿USDC? ¿USDT?) | Añadida nota "⚠ conv. no verificada" y "⚠ asset/conv. no verificado" en tabla de comparación | index.html:~1570 |
| 26 | BCB label decía "Tipo Oficial BCB" sin aclarar intermediario | `officialBuy` viene de DolarBlueBolivia `/v1/officialRate`, no directamente del BCB | Cambiado a "Tasa de referencia BCB" con label "vía API DolarBlueBolivia"; nota de cadena de datos en card detail | index.html:757,759,761 |

---

## Pendientes / Bloqueados (requieren decisión o verificación externa)

| Item | Descripción | Estado |
|---|---|---|
| F — Restricciones bancarias | Límites corregidos a "Con límite mensual"; fechas de revisión requieren verificación manual | Requiere actualización periódica con webs oficiales de cada banco |
| G — Links bancarios | Links apuntan al home del banco; verificar si hay URL directa al tarifario de cada uno | Verificación manual por banco |
| H — Footer links | Operativos. Blog apunta a `/blog/` existente | ✅ Sin pendientes críticos |
| I — Bybit convención | Campo `buy/sell` de `/v1/p2p/bybit` no verificado independientemente de API DolarBlueBolivia | Marcado como convención observada, no documentada |
| J — AirTM asset | `addValue`/`withdrawValue` sugieren USDT pero asset no confirmado (¿AirUSD vs USDT?) | Marcado como convención observada, no documentada |
| K — BCB officialBuy cadena | `official.buy` de `/v1/officialRate` (DolarBlueBolivia), sin verificación directa del BCB | Label ya dice "referencia"; documentar cadena explícitamente |

---

## Validaciones ejecutadas

### Implementado y probado (código)
- ✅ Convención data verificada desde código fuente (`fetch_prices.py` líneas 143-210, `loadPrices()` líneas 1318-1335): cada proveedor confirmado por nombre de campos API, no solo por desigualdad de precios
- ✅ Test case calculadora: sell 100 USDT × 11.82 = Bs 1182 ✓; buy USDT con Bs 1188 ÷ 11.88 = 100 USDT ✓
- ✅ Spread con datos reales: Binance (11.88-11.82)/11.82×100 = 0.51%; Takenos (12.11-11.71)/11.71×100 = 3.42% ✓
- ✅ `calcRatePill` corregido: muestra `binance.buy=11.82` cuando USDT→BOB, `binance.sell=11.88` cuando BOB→USDT
- ✅ `isDataFresh()` añadida: umbral 180 min, alineado con GitHub Actions (cada 2h en días hábiles)
- ✅ Comparador BCB: etiquetas y textos corregidos para no afirmar precios de librecambistas

### Validado en navegador (http://localhost:8091) — 2026-10-11

#### Pruebas de badge de fuente (4 escenarios + caso regresión):
| Escenario | source | lastUpdated | Badge esperado | Resultado |
|---|---|---|---|---|
| 1. Cotización observada y reciente | `api_dbb_eldorado` | ahora | En vivo | ✅ |
| 2. Estimación recién generada | `calculated` | ahora | Estimado | ✅ |
| 3. Cotización observada pero vieja (+5h) | `api_dbb_takenos` | hace 5h | Referencial | ✅ |
| 4. Procedencia ausente | `undefined` | ahora | Referencial | ✅ |
| 5. Source genérico 'live' (pre-4e13cd4) | `'live'` | ahora | Referencial | ✅ detecta el bug anterior |

#### Fuentes actuales en `pricesData` tras reload:
`binance_p2p` ✓ | `api_dbb_eldorado` ✓ | `api_dbb_airtm` ✓ | `api_dbb_bybit` ✓ | `api_dbb_wallbit` ✓

#### Pruebas de proyección (contra `renderPrediction()` real):
| Caso | Entrada | Badge | Correcto |
|---|---|---|---|
| Ascendente | +0.06/día × 14 registros | ↗ Tendencia al alza | ✅ |
| Descendente | -0.06/día × 14 registros | ↘ Tendencia a la baja | ✅ |
| Estable | 0.00/día × 14 registros | → Tendencia estable | ✅ |
| Borde float | +0.05/día exacto | ↗ alza (imprecisión float, slope ≈ 0.0500...01) | documentado — umbral `> 0.05` estricto |

Nota: el umbral es `changeSell > 0.05` (código fuente verificado). Con exactamente 0.05/día la aritmética de punto flotante produce un slope ≈ 0.05+ε, dando "alza". Comportamiento esperado, no un bug del algoritmo.

#### Verificaciones visuales:
- ✅ Bybit: badge "Live" (source=api_dbb_bybit) + nota "⚠ conv. no verificada"
- ✅ AirTM: nota "⚠ asset/conv. no verificado"
- ✅ BCB card: "Tasa de referencia BCB" · "vía API DolarBlueBolivia"
- ✅ Tarjetas bancarias: badge "Con límite mensual" con `data-status="mod"` en todas
- ✅ Banco Fortaleza: badge "Por confirmar"
- ✅ `calculadora-usdt-bolivianos.html` (nombre completo): bugs C1, C2, C3 corregidos

---

---

## Tabla de procedencia por proveedor (estado 2026-10-11)

| Proveedor | Endpoint (Python) | Source en JSON | Source en browser (tras fix) | Convención buy/sell | Estado verificación |
|---|---|---|---|---|---|
| **Binance** | `/v1/officialRate` → `blue.buy/sell` | `"binance_p2p"` (siempre, línea 455) | `'binance_p2p'` | buy < sell (market-centric): buy=usuario vende, sell=usuario compra | ✅ verificado desde `fetch_prices.py` |
| **Eldorado** | `/v1/eldorado` → `buy/sell` | `"api_dbb_eldorado"` o `"calculated"` | preservado del JSON o `'api_dbb_eldorado'` si live OK | buy > sell (user-centric) | ✅ verificado por fallback `buy_price*1.0071 > sell_price*0.9880` |
| **Takenos** | `/v1/takenos` → `buy/sell` | `"api_dbb_takenos"` o `"calculated"` | preservado o `'api_dbb_takenos'` | buy > sell (user-centric) | ✅ verificado por fallback `*1.0222`/`*0.9860` |
| **Wallbit** | `/v1/wallbit` → `buy/sell` | `"api_dbb_wallbit"` o `"calculated"` | preservado o `'api_dbb_wallbit'` | buy > sell (user-centric) | ✅ verificado por fallback `*1.0121`/`*0.9840` |
| **AirTM** | `/v1/airtm` → `addValue/withdrawValue` | `"api_dbb_airtm"` o `"calculated"` | preservado o `'api_dbb_airtm'` | `addValue`=compra (buy), `withdrawValue`=venta (sell) — nombres explícitos | ⚠ **Asset no confirmado** — ¿AirUSD, USDC o USDT? Fees desconocidas. Marcado en UI. |
| **Bybit** | `/v1/p2p/bybit` → `buy/sell` | `"api_dbb_bybit"` o `"calculated"` | preservado o `'api_dbb_bybit'` | buy > sell (user-centric, asumido) | ⚠ **Convención no verificada** desde doc. API. Marcado en UI. Spread actual 0.01 (11.85/11.84). |
| **SaldoAr** | `/v1/saldoar` → `buy/sell` | `"api_dbb_saldoar"` o `"calculated"` | preservado o `'api_dbb_saldoar'` | buy > sell (user-centric) | ✅ verificado por fallback `*1.011`/`*0.988` |
| **BCB official** | `/v1/officialRate` → `official.buy/sell` | **sin campo source** en `bcb_data` | n/a (no en platCard) | n/a — tasa administrativa | ⚠ **Cadena no directa**: DolarBlueBolivia como intermediario. Aclarado en UI como "vía API DolarBlueBolivia". |
| **BCB VRD** | `/v1/referencial/bcb` o scraping `bcb.gob.bo` | en `bcb.vrdBuy/vrdSell` | n/a | n/a | ✅ — doble fuente (API DBB + scraping directo BCB) |

**Fecha del dato usado:** `prices.json.lastUpdated` es la fecha de generación del archivo por GitHub Actions. No hay timestamp por-proveedor. Cuando `loadPrices()` hace refresh exitoso, `base.lastUpdated` se actualiza al momento de la llamada del browser.

---

## Próximo paso: Fase 2

- Verificación visual mobile (pendiente — no ejecutada en esta sesión)
- Confirmar asset de AirTM (USDT vs AirUSD vs USDC) desde documentación oficial AirTM o DolarBlueBolivia
- Confirmar convención Bybit desde documentación oficial o test empírico
- Añadir campo `source` a `bcb_data` en `fetch_prices.py` para completar la cadena
- Actualizar límites bancarios con fechas verificadas desde webs oficiales de cada banco

---

## Fase 2 — Mejora Visual y Experiencia

**Rama:** `fase2-mejora-visual`  
**Fecha:** 2026-10-11  
**Base:** `fase1-auditoria-coherencia` @ `b11c4b4`

### Cambios aplicados

| # | Área | Cambio |
|---|---|---|
| F2-1 | Antigüedad por proveedor | Badge usa `data.fetchedAt` individual, no `_jsonLastUpdated` global. Lógica: `'Estimado'` si calculated · `'En vivo'` si observed+fresco (<3h) · `'Referencial'` si observed+viejo · `'No verificada'` si sin `fetchedAt`. En `renderExchanges()`: badge `?` para proveedores sin `fetchedAt`. |
| F2-2 | Navegación | Simplificada a 5 items: Cotizaciones · Comparadores · Calculadora · Histórico · Guías. Eliminado duplicado "Calculadora". Mobile nav: `role="dialog"`, `aria-modal`, botón con `aria-expanded`/`aria-controls`. |
| F2-3 | Orden de contenido | DOM reordenado + CSS `flex order` actualizado: cotizaciones → calculadora → comparadores (bancos+exchanges) → histórico → BCB → proyección → plataformas → límites → noticias. |
| F2-4 | Tarjetas plataforma | CSS neutralizante: `background: var(--bg2)`, bordes neutros, logos con `saturate(0.7)`. Verde/rojo solo en buy/sell price. |
| F2-5 | Tablas | `font-variant-numeric: tabular-nums`. Precios alineados a la derecha. `overflow-x: auto` en `.ex-table-wrap` y `.banks-table-wrap`. |
| F2-6 | Noticias | Máx. 6 iniciales + botón "Ver N más". Sin descripción duplicada si `desc === title`. Campo `source` visible en card. |
| F2-7 | Footer | Autor "Samuel Ampuero" en `rgba(255,255,255,.85)`. Sin URL de portafolio inventada. |
| F2-8 | Anclas | `scroll-margin-top: 72px` en todas las secciones anchor para compensar cabecera fija. |
| F2-9 | Overflow (v2) | Causa raíz del overflow identificada y corregida: `grid-template-columns: 1fr` en `.calc-wrapper` resolvía a 366px por comportamiento `minmax(auto,1fr)` de CSS Grid. Fix: `minmax(0,1fr)` + `min-width:0` en `.calc-left/.calc-right`. CSS `order:` eliminadas (el DOM ya está en orden correcto; las reglas empujaban el banner Binance `order:0` a posición 1 visualmente). Bug "Ver más": corregido con `tmp.firstChild` (en vez de `.replace('<a ','')` que dejaba atributos sueltos — causaba newsGrid de 6452px). `overflow-x:hidden` eliminado de html/body (ya no necesario). |
| F2-10 | Menú móvil | `toggleMenu()` ahora sincroniza `aria-expanded`. `closeMobileNav()` también resetea `aria-expanded`. Escape cierra el menú vía `document.addEventListener('keydown', …)`. |

### Archivos modificados

- `index.html` — cambios de navegación, orden DOM, CSS, JavaScript (badges, noticias, overflow, aria, calc grid)
- `PROJECT_STATE.md` — esta entrada

### Validación ejecutada (2026-10-11) — cierre de Fase 2

| Viewport | `htmlScrollW` | Calc. OK | Orden visual | Nav/Aria | Noticias "Ver más" | Errores nuevos |
|---|---|---|---|---|---|---|
| 375px | 375px ✅ | 100 USDT→Bs 1182 ✅ | alertStrip→calculator→…→noticias ✅ | aria-expanded true/false, Escape cierra ✅ | 6→14 sin overflow ✅ | Ninguno |
| 768px | 753px ✅ | calc 2 cols (323px×2) ✅ | ✅ | ✅ | ✅ | Ninguno |
| 1440px | 1425px ✅ | ✅ | ✅ | ✅ | ✅ | Ninguno |

- ✅ Nav: 5 links, sin duplicado
- ✅ `scroll-margin-top: 72px` en todas las 10 secciones anchor
- ✅ Calculadora USDT→BOB: 100 × tasa_compra | BOB→USDT: usa tasa_venta (correcto desde Fase 1)
- ✅ Chart tabs: 7D / 30D / 90D / 180D / 1A / MAX / 7d / 15d / 30d / Histórico presentes
- ✅ Bancos toggle buy/sell funciona
- ✅ BCB VRD: muestra datos de `prices.json` (fallback operativo cuando CORS bloquea la llamada en vivo)
- ✅ Orden sin reglas CSS `order:` — DOM es el único origen de orden (consistente con tab/teclado)

### CORS — registro preciso

**Solicitud bloqueada:** `GET https://api.dolarbluebolivia.click/v1/referencial/bcb`  
**Frecuencia:** ~10 intentos por sesión de carga (la función `loadPrices()` reintenta con interval)  
**Causa:** La API no envía cabecera `Access-Control-Allow-Origin` para origen `http://localhost:*`  
**Función afectada:** actualización en vivo del tipo de cambio BCB VRD (tasa del Banco Central)  
**Fallback activo:** la sección BCB VRD muestra el valor de `prices.json` (generado por GitHub Actions), que se actualiza cada ~2h en producción. Muestra "Bs 11.73" en localhost  
**CORRECCIÓN (comprobación posterior, 2026-10-11):** el mismo bloqueo CORS se reproduce también en producción, desde el origen `https://usdt-bolivia.com`. La afirmación anterior de que en producción quedaba resuelto era errónea. Ver sección "Corrección post-publicación" al final.  
**Ninguno de estos errores es nuevo de Fase 2.**

### Pendientes / Limitaciones

- Confirmar convención Bybit y asset AirTM (heredado de Fase 1)
- La consulta en vivo a `/v1/referencial/bcb` está bloqueada por CORS también en producción; el VRD usa el respaldo de `prices.json` (ver sección final)
- Actualizar límites bancarios con fechas verificadas desde webs oficiales

---

## Publicación — 2026-10-11

**Merge ejecutado:** `fase2-mejora-visual` → `main` mediante `--no-ff`

| Referencia | SHA |
|---|---|
| SHA previo de producción (main antes del merge) | `a955add` |
| SHA merge commit | `7d1b36e` |
| Parent 1 (main) | `a955add` |
| Parent 2 (punta fase2) | `4145031` |

**Push:** `git push origin main` sin force — resultado: `a955add..7d1b36e main → main`

**GitHub Pages:** `build_type: legacy`, rama `main:/`, estado `built` confirmado por API tras el push.

**Workflow `update-prices.yml`:** activo en `main`, opera independientemente; no afectado por el merge.

### Verificaciones post-publicación en usdt-bolivia.com

| Verificación | Resultado |
|---|---|
| Nav 5 ítems (Cotizaciones / Comparadores / Calculadora / Histórico / Guías) | ✅ |
| `htmlScrollW ≤ vw` a 375px | ✅ 410 ≤ 426 |
| `htmlScrollW ≤ vw` a 1440px | ✅ 1425 ≤ 1440 |
| `scroll-margin-top: 72px` en `#calculator` | ✅ |
| Badges de procedencia (`Live`, `?`) presentes | ✅ |
| Noticias: 6 iniciales + botón "Ver más" | ✅ |
| Noticias expandidas: fuente visible, sin desbordamiento | ✅ |
| Calculadora: `1 USDT = 11.82 BOB`, tasa P2P | ✅ |
| Comparador de bancos: tabla con ranking y precios tabulares | ✅ |
| BCB VRD en producción | **Afirmación retirada.** Se anotó "En vivo" y "CORS resuelto" sin evidencia suficiente: una comprobación posterior mostró el bloqueo CORS también desde `usdt-bolivia.com`. El valor mostrado proviene del respaldo `prices.json` (ver sección final) |

### Reversión disponible (si fuera necesaria)

```bash
# Revertir el merge conservando historial
git revert -m 1 7d1b36e   # -m 1 = parent main (a955add) es el mainline
git push origin main
```
`-m 1` revierte todos los cambios incorporados por el merge (8 commits de Fase 1+2) sin reescribir el historial. Ejecutar solo ante regresión funcional confirmada.

---

## Corrección post-publicación — 2026-10-11

### 1. CORS en `/v1/referencial/bcb` (corrige afirmaciones previas de Fase 2)

- **Comprobado:** cargando `https://usdt-bolivia.com/` (producción) en Chrome, la consola registra `Access to fetch at 'https://api.dolarbluebolivia.click/v1/referencial/bcb' from origin 'https://usdt-bolivia.com' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present`. Igual desde `localhost`.
- **Efecto:** la actualización directa del VRD/BCB desde el navegador **no funciona**; el sitio usa el respaldo de `data/prices.json` (generado por GitHub Actions). Los demás endpoints consultados (`officialRate`, `eldorado`, `takenos`, `wallbit`, `airtm`, `bybit`, `saldoar`) sí respondieron en las pruebas de esta sesión.
- **Se retiran** las notas previas "CORS resuelto en producción" y "BCB VRD en vivo". Sin cambios de código en esa consulta; pendiente: servir el VRD solo desde `fetch_prices.py` o usar un proxy propio.

### 2. Textos de frecuencia de actualización

Qué es cada cosa (ahora se distingue en la interfaz):
- **Actualización programada:** GitHub Actions ejecuta `fetch_prices.py` y publica `data/prices.json` a las 12–22 UTC (L–V, cada 2 h) y 00 y 02 UTC (M–S). No hay garantía de ejecución puntual; GitHub puede retrasar los cron.
- **Consulta exitosa por proveedor:** el navegador consulta cada endpoint al cargar la página. Solo si ese proveedor responde se guarda `fetchedAt`; si falla se conserva el dato del archivo, sin marca de hora propia.

Cambios (index.html, calculadora, blog, página de cotización del 6-oct):
- Eliminados "tiempo real", "En vivo", "Actualizado cada hora", "actualizada/o automáticamente" y "sin demoras".
- Hero: la hora mostrada era la del reloj del visitante (`new Date()`), no la del dato. Ahora muestra "Última consulta exitosa: …" (hora Bolivia) o "Archivo programado generado: …" si ninguna consulta respondió.
- Insignia de la tarjeta: `CONSULTA ACTUAL` / `ARCHIVO GUARDADO`. Tarjetas de plataforma: `Consulta exitosa` · `Consulta anterior` · `Archivo programado` · `Estimado`; cada una con su propia hora solo si hubo consulta ("consulta …"); si no, "archivo generado …", que es la fecha global de generación de `prices.json`, no la hora de esa cotización. Tabla: `Consulta` / `Ant.` / `Arch.` / `Est.`.
- `base.lastUpdated` ya no se pone a "ahora" si todos los proveedores fallan.
- Verificado en navegador local: con consulta exitosa y con las consultas bloqueadas (ambos caminos). Único error de consola: el CORS ya descrito.

### 3. Limitaciones que siguen abiertas

- `prices.json` no guarda marca de hora por proveedor, solo `lastUpdated` global; por tanto el dato de archivo no puede indicar su antigüedad individual.
- Pizarras de bancos y noticias: solo existen en el archivo programado; no hay consulta directa. El texto "publicadas por cada banco en su web oficial" fue sustituido por "obtenidas vía API de terceros" porque `fetch_prices.py` las lee de `/v1/bancos` (DolarBlueBolivia), no de cada banco.
- Pendientes heredados: convención de Bybit, activo de AirTM, límites bancarios con fechas verificadas.
- Estos cambios están en el árbol de trabajo, sin commit ni push (rama `main`).

### 4. Seguridad

- La URL del remoto `origin` contenía un token en texto plano; se reemplazó por `https://github.com/samu-ac/usdt-bolivia.git` y se censuró una línea del reflog local. El token **sigue válido hasta revocarlo en GitHub** (Settings → Developer settings → Personal access tokens).
