from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MensajeEntrante:
    telefono: str
    texto: str
    nombre: Optional[str] = None
    tipo: str = "text"
    media_id: Optional[str] = None


class ProveedorWhatsApp(ABC):
    @abstractmethod
    def validar_webhook(self, params: dict) -> Optional[str]:
        """Valida el challenge de verificación del webhook (GET)."""

    @abstractmethod
    def parsear_webhook(self, payload: dict) -> Optional[MensajeEntrante]:
        """Extrae un MensajeEntrante del payload crudo del webhook (POST)."""

    def validar_firma(self, cuerpo: bytes, firma: Optional[str]) -> bool:
        """Valida la firma del webhook (POST). Default: sin validación."""
        return True

    @abstractmethod
    async def enviar_mensaje(
        self, 
        telefono: str, 
        texto: str, 
        botones: Optional[list[dict]] = None,
        template: Optional[dict] = None,
        documento: Optional[dict] = None
    ) -> Any:
        """Envía un mensaje de texto (y opcionalmente botones, template o documento) al número dado."""
