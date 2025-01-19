import tempfile
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import json
import base64
from dotenv import load_dotenv
load_dotenv()



def create_temp_token():
    temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.json')
    temp_file.close()
    dir = temp_file.name.split('\\')
    dir = '\\'.join(dir[:-1])
    dir = dir + '\\' + 'token.json'
    dir = os.path.abspath(dir)
    if not os.path.exists(dir):
        os.rename(temp_file.name, dir)
        return dir
    else:
        return dir
def download_folder_file(service, file_id, file_path):
    try:
        # Get file metadata to check MIME type
        file_metadata = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        file_name = file_metadata['name']
        mime_type = file_metadata['mimeType']
        
        # Export MIME types and corresponding extensions
        export_mime_types = {
            'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
            'application/vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
            'application/vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')
        }
        
        if mime_type in export_mime_types:
            export_mime_type, extension = export_mime_types[mime_type]
            request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            file_path += extension  # Append the correct extension
        else:
            # For non-Google native files, download directly
            request = service.files().get_media(fileId=file_id)
        
        # Download the file
        with open(file_path, 'wb') as file:
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        print(f"{file_name} downloaded successfully to {file_path}")
    
    except HttpError as error:
        print(f"An error occurred: {error}")
        
def authenticate_user():
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/drive']
    eda_creds= os.getenv('EDA_CREDENTIALS')
    eda_creds = base64.b64decode(eda_creds).decode('utf-8')
    eda_creds = json.loads(eda_creds)
    token = create_temp_token()
    if os.path.exists(token):
        with open(token, 'r') as f:
            cached_token = f.read()
            if cached_token.strip() == '':
                flow = InstalledAppFlow.from_client_config(eda_creds, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(token, 'w') as token_file:
                    token_file.write(creds.to_json())
        creds = Credentials.from_authorized_user_file(token, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                eda_creds, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        with open(token, 'w') as token_file:
            token_file.write(creds.to_json())

    return creds