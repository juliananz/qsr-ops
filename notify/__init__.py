"""
notify — Generación y envío de reportes de turno para Astro Burger.

Diseño:
- report_text(): arma el texto plano del reporte (canal-agnóstico).
- report_image(): renderiza ese mismo reporte como PNG (Pillow, puro texto).
- send_whatsapp(): dispara el mensaje. Dos backends intercambiables:
    "link"  -> genera URL wa.me (disparo manual, gratis, sin API)
    "cloud" -> WhatsApp Cloud API de Meta (oficial, requiere credenciales)

El formateo NO depende del canal. Si mañana cambias de backend,
no tocas report_text() ni report_image().
"""
from .report import report_text, report_image, ShiftReport, ReportLine
from .send import send_whatsapp, wa_me_link

__all__ = [
    "report_text",
    "report_image",
    "ShiftReport",
    "ReportLine",
    "send_whatsapp",
    "wa_me_link",
]
