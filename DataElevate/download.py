import GoogleDrive_api
import kaggle_api
import kagglehub #type: ignore
import os
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from io import BytesIO
import requests
import io
from tqdm import tqdm
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import base64
import json
import tempfile
import shutil
from urllib.parse import urlparse
from EDAerror import InvalidInput

load_dotenv()

class Download_data:

    class Kaggle:

        @staticmethod
        def from_kaggle(dataset_path, to_path=None):
            if 'ID' == kaggle_api.check_input_type(dataset_path):
                dataset_url = f"https://www.kaggle.com/datasets/{dataset_path}"
            elif 'URL' == kaggle_api.check_input_type(dataset_path):
                dataset_url = dataset_path
            else:
                raise InvalidInput("Invalid Dataset URL/ID.")

            if kaggle_api.is_kaggle_url_valid(dataset_url):
                if 'ID' == kaggle_api.check_input_type(dataset_path):
                    folder_path = kagglehub.dataset_download(f"{dataset_path}")
                else:
                    dataset_path = kaggle_api.extract_kaggle_dataset_name(dataset_url)
                    folder_path = kagglehub.dataset_download(f"{dataset_path}")

                # Get the list of files in the downloaded folder
                files = os.listdir(folder_path)
            else:
                raise InvalidInput("Invalid dataset URL/ID.")
            
            match = re.search(r'[^/]+(?=$)', dataset_path)
            foldername = match.group(0)
            if to_path is None:
                to_path = os.getcwd()
                to_path = os.path.join(to_path, f'Data/{foldername}')
                print(to_path)
                kaggle_api.get_kaggle_files(folder_path, files, to_path)
                kaggle_api.remove_cache_data(folder_path)
            elif to_path:
                kaggle_api.get_kaggle_files(folder_path, files, to_path)
                kaggle_api.remove_cache_data(folder_path)
            
            files_paths = []
            for file in files:
                files_path = os.path.join(to_path, file)
                files_paths.append(files_path)

            return files_paths

    class GoogleDrive:
        @staticmethod
        def get_file_id(link):
            if len((link).strip()) > 0:
                if "/" in link:
                    parts = link.split('/')
                    if 'folders' in parts:
                        return parts[-1]
                    elif 'file' in parts:
                        return parts[5]
                    elif 'docs.google.com' in parts:
                        return parts[-2]
                    else:
                        raise ValueError("Invalid Google Drive link")
                else:
                    return link
            else:
                raise ValueError("Invalid Google Drive link")

        @staticmethod
        def download_folder(folder_id, folder_path=None):
            creds = GoogleDrive_api.authenticate_user()
            service = build('drive', 'v3', credentials=creds)
            folder_path = folder_path or os.path.join(os.getcwd(), 'GoogleDrive_Data')
            os.makedirs(folder_path, exist_ok=True)
            folder_id = Download_data.GoogleDrive.get_file_id(folder_id)

            query = f"'{folder_id}' in parents and trashed = false"
            results = service.files().list(q=query, fields="files(id, name, mimeType)", includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
            items = results.get('files', [])

            if not items:
                print(f"No files found in folder: {folder_id}")
            else:
                folder_name = os.path.basename(folder_path)
                pbar = tqdm(total=len(items), desc=f"Processing {folder_name} folder.", position=0)

                for item in items:
                    file_id = item['id']
                    file_name = item['name']
                    mime_type = item['mimeType']

                    if mime_type == 'application/vnd.google-apps.folder':
                        subfolder_path = os.path.join(folder_path, file_name)
                        Download_data.GoogleDrive.download_folder(file_id, subfolder_path)
                        subfolder_items = service.files().list(q=f"'{file_id}' in parents and trashed = false", fields="files(id)").execute().get('files', [])
                        pbar.total += len(subfolder_items)
                        pbar.refresh()
                    else:
                        GoogleDrive_api.download_folder_file(service, file_id, os.path.join(folder_path, file_name))
                    pbar.update(1)
                pbar.close()

        @staticmethod
        def download_file(url, folder_path=None):
            creds = GoogleDrive_api.authenticate_user()
            service = build('drive', 'v3', credentials=creds)

            try:
                file_id = Download_data.GoogleDrive.get_file_id(url)
                file_metadata = service.files().get(fileId=file_id, fields="name, mimeType").execute()
                file_name = file_metadata['name']
                mime_type = file_metadata['mimeType']

                if folder_path is None:
                    folder_path = os.getcwd()
                    folder_path = os.path.join(folder_path, "GoogleDrive_Data")
                os.makedirs(folder_path, exist_ok=True)

                export_mime_types = {
                    'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
                    'application/vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
                    'application/vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')
                }

                if mime_type in export_mime_types:
                    export_mime_type, extension = export_mime_types[mime_type]
                    request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
                    file_name += extension
                else:
                    request = service.files().get_media(fileId=file_id)

                filepath = os.path.join(folder_path, file_name)

                with io.FileIO(filepath, 'wb') as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()

                return f"{file_name} downloaded successfully."

            except HttpError as error:
                return f"An error occurred: {error}"