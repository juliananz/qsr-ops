"""
notify.report — Modelo de datos del reporte de turno + renderizadores
(texto plano y PNG). Sin dependencias del canal de envío.
"""
from __future__ import annotations

import os
import textwrap
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from core.config import BUSINESS_TZ

# ---------------------------------------------------------------------------
# Fuentes. DejaVu viene en casi cualquier Linux; si no está, Pillow usa default.
# ---------------------------------------------------------------------------
_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "C:/Windows/Fonts",  # Windows (la PC del negocio)
]


def _find_font(names: list[str]) -> Optional[str]:
    for d in _FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


_MONO = _find_font(["DejaVuSansMono.ttf", "consola.ttf", "cour.ttf"])
_SANS = _find_font(["DejaVuSans.ttf", "arial.ttf", "segoeui.ttf"])
_SANS_BOLD = _find_font(["DejaVuSans-Bold.ttf", "arialbd.ttf", "segoeuib.ttf"])


def _font(path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------
@dataclass
class ReportLine:
    """Una línea etiqueta -> valor dentro de una sección del reporte."""
    label: str
    value: str
    emphasis: bool = False  # negrita / resaltado (totales)


@dataclass
class ShiftReport:
    """
    Reporte de un turno (o consolidado del día).

    Pensado para alimentarse desde close_shift de qsr-ops, pero es genérico:
    cualquier conjunto de secciones con líneas etiqueta->valor.
    """
    title: str                      # "Astro Burger — Corte Turno 1"
    subtitle: str = ""              # "Jueves 29 may 2026 · José Julián"
    sections: dict[str, list[ReportLine]] = field(default_factory=dict)
    footer: str = ""                # nota libre / comentarios del checklist

    def add(self, section: str, label: str, value, emphasis: bool = False) -> None:
        self.sections.setdefault(section, []).append(
            ReportLine(label, _fmt(value), emphasis)
        )


def _fmt(v) -> str:
    if isinstance(v, bool):
        return "Sí" if v else "No"
    if isinstance(v, (int,)):
        return f"{v:,}"
    if isinstance(v, float):
        # dinero / cantidades con decimales
        return f"{v:,.2f}"
    return str(v)


def money(v: float) -> str:
    return f"${v:,.2f}"


# ---------------------------------------------------------------------------
# Renderizador de TEXTO
# ---------------------------------------------------------------------------
def report_text(r: ShiftReport, width: int = 38) -> str:
    """
    Texto plano monoespaciado, listo para pegar en WhatsApp.
    width = ancho de caracteres antes del alineado de columnas.
    """
    out: list[str] = []
    sep = "━" * width
    out.append(f"*{r.title}*")
    if r.subtitle:
        out.append(r.subtitle)
    out.append(sep)

    for sec_name, lines in r.sections.items():
        out.append(f"*{sec_name}*")
        for ln in lines:
            label = ln.label
            value = ln.value
            # alineado: etiqueta a la izquierda, valor a la derecha
            dots = max(1, width - len(label) - len(value))
            line = f"{label}{'.' * dots}{value}"
            if ln.emphasis:
                line = f"*{label}* {' ' * max(1, dots - 2)}*{value}*"
            out.append(line)
        out.append("")

    if r.footer:
        out.append(sep)
        out.append(r.footer)

    out.append(f"_Generado {datetime.now(ZoneInfo(BUSINESS_TZ)):%d/%m %H:%M}_")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Renderizador de IMAGEN (PNG)
# ---------------------------------------------------------------------------
# Paleta sobria (legible en pantalla de celular)
_BG = (250, 250, 248)
_INK = (28, 28, 30)
_MUTED = (110, 110, 116)
_ACCENT = (190, 60, 40)      # rojo "burger"
_RULE = (220, 220, 216)
_EMPH_BG = (242, 238, 230)


def report_image(r: ShiftReport, path: str, width_px: int = 720) -> str:
    """
    Renderiza el reporte como PNG y lo guarda en `path`. Devuelve `path`.
    Hace un pase de medición para calcular alto exacto (sin recortes).
    """
    pad = 36
    f_title = _font(_SANS_BOLD, 34)
    f_sub = _font(_SANS, 20)
    f_sec = _font(_SANS_BOLD, 23)
    f_row = _font(_MONO, 21)
    f_foot = _font(_SANS, 18)

    content_w = width_px - 2 * pad

    # ---- pase 1: medir alto ----
    def line_h(font) -> int:
        asc, desc = font.getmetrics()
        return asc + desc + 6

    y = pad
    y += line_h(f_title)
    if r.subtitle:
        y += line_h(f_sub)
    y += 14  # regla
    for sec_name, lines in r.sections.items():
        y += 10 + line_h(f_sec)
        for ln in lines:
            y += line_h(f_row) + (6 if ln.emphasis else 0)
        y += 8
    if r.footer:
        wrapped = textwrap.wrap(r.footer, width=58) or [""]
        y += 14 + len(wrapped) * line_h(f_foot)
    y += line_h(f_foot)  # timestamp
    height = y + pad

    # ---- pase 2: dibujar ----
    img = Image.new("RGB", (width_px, height), _BG)
    d = ImageDraw.Draw(img)
    y = pad

    d.text((pad, y), r.title, font=f_title, fill=_ACCENT)
    y += line_h(f_title)
    if r.subtitle:
        d.text((pad, y), r.subtitle, font=f_sub, fill=_MUTED)
        y += line_h(f_sub)
    y += 6
    d.line([(pad, y), (width_px - pad, y)], fill=_RULE, width=2)
    y += 8

    for sec_name, lines in r.sections.items():
        y += 10
        d.text((pad, y), sec_name, font=f_sec, fill=_INK)
        y += line_h(f_sec)
        for ln in lines:
            row_h = line_h(f_row)
            if ln.emphasis:
                d.rectangle([(pad - 6, y - 2),
                             (width_px - pad + 6, y + row_h + 2)],
                            fill=_EMPH_BG)
            # etiqueta izq, valor der
            d.text((pad, y), ln.label, font=f_row, fill=_INK)
            vw = d.textlength(ln.value, font=f_row)
            color = _ACCENT if ln.emphasis else _INK
            d.text((width_px - pad - vw, y), ln.value, font=f_row, fill=color)
            y += row_h + (6 if ln.emphasis else 0)
        y += 8

    if r.footer:
        y += 6
        d.line([(pad, y), (width_px - pad, y)], fill=_RULE, width=2)
        y += 8
        for w in (textwrap.wrap(r.footer, width=58) or [""]):
            d.text((pad, y), w, font=f_foot, fill=_MUTED)
            y += line_h(f_foot)

    d.text((pad, y), f"Generado {datetime.now(ZoneInfo(BUSINESS_TZ)):%d/%m/%Y %H:%M}",
           font=f_foot, fill=_MUTED)

    img.save(path, "PNG", optimize=True)
    return path
