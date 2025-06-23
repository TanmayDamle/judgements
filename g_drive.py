import io
import os
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import json

SCOPES = ['https://www.googleapis.com/auth/drive.file']
# CREDENTIALS_FILE = 'credentials.json'

from tempfile import NamedTemporaryFile

# Load from env and write to temp file
credentials = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
temp_file = NamedTemporaryFile(delete=False, suffix=".json", mode="w")
json.dump(credentials, temp_file)
temp_file.close()
CREDENTIALS_FILE = temp_file.name

# In-memory storage of ongoing flows keyed by state
flows = {}

def initiate_google_auth_flow():
    REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/oauth2callback")

    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true'
    )
    flows[state] = flow
    return auth_url, state

def exchange_code_for_service(state: str, code: str):
    flow = flows.pop(state, None)
    if not flow:
        raise ValueError("Invalid OAuth state.")
    flow.fetch_token(code=code)
    service = build('drive', 'v3', credentials=flow.credentials)
    return service

def file_exists_on_drive(service, file_id):
    try:
        service.files().get(fileId=file_id, fields="id").execute()
        return True
    except HttpError as e:
        if e.resp.status == 404:
            return False
        raise e



def upload_pdf(service, file_content: bytes, filename: str, folder_name="judgements"):
    # Ensure target folder exists or create it
    results = service.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false",
        spaces='drive',
        fields='files(id,name)',
        pageSize=10
    ).execute()
    items = results.get('files', [])
    if items:
        folder_id = items[0]['id']
    else:
        folder = service.files().create(
            body={'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'},
            fields='id'
        ).execute()
        folder_id = folder.get('id')

    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/pdf')
    file = service.files().create(
        body={'name': filename, 'parents': [folder_id]},
        media_body=media,
        fields='id'
    ).execute()
    return file.get('id')
