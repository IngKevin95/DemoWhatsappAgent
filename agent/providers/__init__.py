import os

from .base import ProveedorWhatsApp
from .meta import ProveedorMeta


def obtener_proveedor() -> ProveedorWhatsApp:
    proveedor = os.getenv("WHATSAPP_PROVIDER", "meta")
    if proveedor == "meta":
        return ProveedorMeta()
    raise ValueError(f"Proveedor no soportado: {proveedor}")
