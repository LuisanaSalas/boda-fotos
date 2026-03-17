import io
import os
import mimetypes
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

BASE_DIR = Path(__file__).resolve().parent.parent

SCOPES = ['https://www.googleapis.com/auth/drive.file']

CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"
TOKEN_FILE = BASE_DIR / "token.json"

FOLDER_ID = "1FubiqfvdWw6zcj5YPfAtRLnq2kkJHN7z"


def get_credentials():
    creds = None

    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            creds = None

    # Si el token existe pero expiró, intenta renovarlo
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
            return creds
        except Exception:
            creds = None

    # Si no hay credenciales válidas, vuelve a pedir login
    if not creds or not creds.valid:
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
            except Exception:
                pass

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_FILE),
            SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def upload_file_to_drive(file_path, filename, table_number=None, guest_name=None):
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    display_name = guest_name.strip() if guest_name else "Invitado"
    safe_name = display_name.replace(" ", "_")

    if table_number:
        final_name = f"Mesa_{table_number}_{safe_name}_{filename}"
    else:
        final_name = filename

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    file_metadata = {
        "name": final_name,
        "parents": [FOLDER_ID]
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes),
        mimetype=mime_type,
        resumable=False
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    return file.get("id")