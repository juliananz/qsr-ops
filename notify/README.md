# notify — Reportes de turno (texto + imagen + WhatsApp)

Módulo canal-agnóstico para qsr-ops. El formateo del reporte NO depende
del método de envío, así que cambiar de backend no obliga a reescribir nada.

## Uso desde close_shift

```python
from notify import report_text, report_image, send_whatsapp
from notify.report import ShiftReport, money

r = ShiftReport(title="Astro Burger — Corte Turno 1",
                subtitle="Jueves 29 may 2026 · Paulina")
r.add("Ventas", "Efectivo", money(4820))
r.add("Ventas", "Total ventas", money(9855.50), emphasis=True)
r.footer = "Checklist: planchas ✓ · faltan servilletas."

txt = report_text(r)                       # texto plano para WhatsApp
img = report_image(r, "corte_t1.png")      # PNG renderizado
res = send_whatsapp("528441234567", txt, img, backend="link")
# res["url"] -> abrir para enviar con un toque
```

## Backends de envío

| backend | costo | imagen automática | desatendido | requisitos |
|---------|-------|-------------------|-------------|------------|
| `link`  | gratis | no (se comparte aparte) | no (un toque) | ninguno |
| `cloud` | por conversación | sí | sí | WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, número Business |

Para activar Cloud API: `pip install requests`, registra un número en
Meta Business, exporta las dos variables de entorno y usa `backend="cloud"`.

## Reporte consolidado del día (Turno 2)
El segundo corte del día debe llevar totales del día completo, no solo del
turno 2. Arma un ShiftReport con secciones "Turno 2" y "Total del día".
