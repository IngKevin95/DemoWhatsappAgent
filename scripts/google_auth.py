"""Corre una vez para autorizar la cuenta de Google y generar token.json.
Requiere credentials.json (OAuth client "Desktop app") en la raíz del repo.
"""
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/gmail.send"]
ROOT = os.path.join(os.path.dirname(__file__), "..")

if __name__ == "__main__":
    flow = InstalledAppFlow.from_client_secrets_file(os.path.join(ROOT, "credentials.json"), SCOPES)
    creds = flow.run_local_server(port=8765)
    with open(os.path.join(ROOT, "token.json"), "w") as f:
        f.write(creds.to_json())
    print("token.json generado.")
