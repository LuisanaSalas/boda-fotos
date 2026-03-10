import io
import os
import re
from pathlib import Path
from datetime import datetime

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

BASE_DIR = Path(__file__).resolve().parent.parent

SCOPES = ['https://www.googleapis.com/auth/drive.file']

CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"
TOKEN_FILE = BASE_DIR / "token.json"

FOLDER_ID = "1FubiqfvdWw6zcj5YPfAtRLnq2kkJHN7z"


def get_credentials():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def sanitize_text(value):
    if not value:
        return "Anonimo"

    value = value.strip()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^A-Za-z0-9_áéíóúÁÉÍÓÚñÑ-]", "", value)

    return value or "Anonimo"


def build_drive_filename(original_filename, guest_name):
    extension = Path(original_filename).suffix.lower() or ".jpg"
    safe_name = sanitize_text(guest_name)
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    return f"{safe_name}_{timestamp}{extension}"


def get_or_create_table_folder(service, table_number):
    folder_name = f"Mesa_{table_number}"

    query = (
        f"name='{folder_name}' "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and '{FOLDER_ID}' in parents "
        f"and trashed=false"
    )

    results = service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    folders = results.get("files", [])

    if folders:
        return folders[0]["id"]

    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [FOLDER_ID],
    }

    folder = service.files().create(
        body=folder_metadata,
        fields="id"
    ).execute()

    return folder["id"]


def upload_file_to_drive(file_obj, original_filename, table_number, guest_name=None):
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    table_folder_id = get_or_create_table_folder(service, table_number)
    drive_filename = build_drive_filename(original_filename, guest_name)

    file_metadata = {
        "name": drive_filename,
        "parents": [table_folder_id]
    }

    file_obj.seek(0)

    media = MediaIoBaseUpload(
        io.BytesIO(file_obj.read()),
        mimetype=getattr(file_obj, "content_type", "application/octet-stream")
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,name"
    ).execute()

    return file