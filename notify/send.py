"""
notify.send — Disparo del mensaje de WhatsApp. Dos backends intercambiables.

Backend "link"  (default): genera una URL wa.me con el texto pre-cargado.
    Gratis, sin API, sin credenciales. El usuario da un toque para enviar.
    Limitación de WhatsApp: wa.me NO puede adjuntar la imagen automáticamente;
    la imagen se comparte aparte (o se usa el backend cloud).

Backend "cloud" : WhatsApp Cloud API de Meta. Oficial, desatendido, soporta
    imagen. Requiere WHATSAPP_TOKEN y WHATSAPP_PHONE_ID en el entorno y un
    número de WhatsApp Business registrado. Stub listo para activar.
"""
from __future__ import annotations

import os
import urllib.parse
from typing import Optional


def wa_me_link(phone: str, text: str) -> str:
    """
    Construye una URL wa.me con el texto pre-cargado.
    phone: número en formato internacional sin '+' ni espacios, ej '5218441234567'.
    """
    phone = "".join(ch for ch in phone if ch.isdigit())
    return f"https://wa.me/{phone}?text={urllib.parse.quote(text)}"


def _send_cloud(phone: str, text: str, image_path: Optional[str]) -> dict:
    """
    Envío vía WhatsApp Cloud API. Requiere:
      WHATSAPP_TOKEN     - token permanente de la app de Meta
      WHATSAPP_PHONE_ID  - ID del número emisor (no el número, el ID)
    Para imagen, Cloud API requiere subir el media primero (/media) y luego
    referenciar el id devuelto. Eso queda implementado abajo.
    """
    import requests  # import perezoso: solo si se usa este backend

    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("WHATSAPP_PHONE_ID")
    if not token or not phone_id:
        raise RuntimeError(
            "Faltan WHATSAPP_TOKEN / WHATSAPP_PHONE_ID en el entorno. "
            "Configúralos o usa backend='link'."
        )

    base = f"https://graph.facebook.com/v20.0/{phone_id}"
    headers = {"Authorization": f"Bearer {token}"}
    phone = "".join(ch for ch in phone if ch.isdigit())

    media_id = None
    if image_path:
        with open(image_path, "rb") as fh:
            up = requests.post(
                f"{base}/media",
                headers=headers,
                files={"file": (os.path.basename(image_path), fh, "image/png")},
                data={"messaging_product": "whatsapp", "type": "image/png"},
                timeout=30,
            )
        up.raise_for_status()
        media_id = up.json().get("id")

    if media_id:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "image",
            "image": {"id": media_id, "caption": text[:1024]},
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        }

    resp = requests.post(f"{base}/messages", headers=headers,
                         json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def send_whatsapp(
    phone: str,
    text: str,
    image_path: Optional[str] = None,
    backend: str = "link",
) -> dict:
    """
    Envía (o prepara) un mensaje de WhatsApp.

    Devuelve un dict con la info relevante según el backend:
      link  -> {"backend": "link", "url": ..., "image_path": ...}
      cloud -> respuesta JSON de la Graph API
    """
    if backend == "link":
        return {
            "backend": "link",
            "url": wa_me_link(phone, text),
            "image_path": image_path,  # se comparte aparte
        }
    if backend == "cloud":
        return _send_cloud(phone, text, image_path)
    raise ValueError(f"backend desconocido: {backend!r}")
