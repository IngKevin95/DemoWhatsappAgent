"""Fallback responses when services degrade."""

import logging

logger = logging.getLogger(__name__)

FALLBACK_RESPONSES = {
    "gemini_timeout": "Disculpa, estoy un poco lento. Intenta de nuevo en unos segundos.",
    "gemini_error": "Hubo un problema procesando tu pregunta. Intenta más tarde.",
    "google_calendar_timeout": "Tu cita se agendar pronto. Te enviaré los detalles a WhatsApp.",
    "google_calendar_error": "No pude agendar ahora. Un agente te llamará pronto.",
    "espocrm_escalation_fail": "Tu caso fue registrado. Un agente te contactará pronto.",
    "espocrm_lead_fail": "Gracias por tu interés. Nos pondremos en contacto pronto.",
    "firebird_license_fail": "Tu estado de licencia se verificará más tarde.",
    "firebird_error": "Sistema de licencias no disponible. Validaremos después.",
}


def get_fallback(service: str, error_type: str, user_phone: str = "unknown") -> str:
    """Get fallback response for service error.

    Args:
        service: Service name (gemini, google_calendar, espocrm, firebird)
        error_type: Error type (timeout, error, etc.)
        user_phone: User phone for logging

    Returns:
        Fallback response message
    """
    key = f"{service}_{error_type}"
    response = FALLBACK_RESPONSES.get(key, "Intenta más tarde, por favor.")

    logger.warning(
        f"Fallback response used for {service}",
        extra={
            "service": service,
            "error_type": error_type,
            "user_phone": user_phone,
        },
    )

    return response
