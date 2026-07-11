import base64
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/gmail.send"]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
HORARIOS_DISPONIBLES = ["09:00", "10:30", "14:00", "16:00"]
TZ_OFFSET = "-05:00"  # America/Bogota, sin DST


def _credentials() -> Credentials:
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def get_calendar_service():
    return build("calendar", "v3", credentials=_credentials())


def get_gmail_service():
    return build("gmail", "v1", credentials=_credentials())


def crear_evento_calendar(
    nombre: str, telefono: str, motivo: str, fecha: str, hora: str,
    calendar_id: str = CALENDAR_ID, correo_cliente: str | None = None,
) -> dict:
    inicio_dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    fin_dt = inicio_dt + timedelta(hours=1)
    evento = {
        "summary": f"Cita SysPlus - {nombre}",
        "description": f"Motivo: {motivo}\nTeléfono: {telefono}",
        "start": {"dateTime": inicio_dt.isoformat(), "timeZone": "America/Bogota"},
        "end": {"dateTime": fin_dt.isoformat(), "timeZone": "America/Bogota"},
    }
    send_updates = "none"
    if correo_cliente:
        evento["attendees"] = [{"email": correo_cliente}]
        send_updates = "all"
    return get_calendar_service().events().insert(
        calendarId=calendar_id, body=evento, sendUpdates=send_updates
    ).execute()


def horarios_libres(fecha: str, calendar_id: str = CALENDAR_ID, hora_inicio: str = "09:00", hora_fin: str = "18:00") -> list[str]:
    """Franjas de HORARIOS_DISPONIBLES (dentro de [hora_inicio, hora_fin)) sin choque
    con eventos reales del calendario calendar_id ese día."""
    inicio_dia = datetime.strptime(fecha, "%Y-%m-%d")
    fin_dia = inicio_dia + timedelta(days=1)
    body = {
        "timeMin": inicio_dia.isoformat() + TZ_OFFSET,
        "timeMax": fin_dia.isoformat() + TZ_OFFSET,
        "items": [{"id": calendar_id}],
    }
    resp = get_calendar_service().freebusy().query(body=body).execute()
    ocupados = [
        (datetime.fromisoformat(b["start"]).replace(tzinfo=None), datetime.fromisoformat(b["end"]).replace(tzinfo=None))
        for b in resp["calendars"][calendar_id]["busy"]
    ]
    libres = []
    for h in HORARIOS_DISPONIBLES:
        if not (hora_inicio <= h < hora_fin):
            continue
        inicio = datetime.strptime(f"{fecha} {h}", "%Y-%m-%d %H:%M")
        fin = inicio + timedelta(hours=1)
        if not any(inicio < b_fin and fin > b_inicio for b_inicio, b_fin in ocupados):
            libres.append(h)
    return libres


def enviar_email(destinatario: str, asunto: str, cuerpo: str) -> dict:
    mensaje = MIMEText(cuerpo)
    mensaje["to"] = destinatario
    mensaje["subject"] = asunto
    raw = base64.urlsafe_b64encode(mensaje.as_bytes()).decode()
    return get_gmail_service().users().messages().send(userId="me", body={"raw": raw}).execute()
