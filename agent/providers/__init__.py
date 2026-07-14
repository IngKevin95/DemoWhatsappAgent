import os

from .base import ProveedorWhatsApp
from .meta import ProveedorMeta


from .telegram import ProveedorTelegram

def obtener_proveedor(canal: str = "meta") -> ProveedorWhatsApp:
    if canal == "meta":
        return ProveedorMeta()
    elif canal == "telegram":
        return ProveedorTelegram()
    raise ValueError(f"Proveedor no soportado: {canal}")
