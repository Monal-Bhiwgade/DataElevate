import shutil
import os
import EDAerror
import re
import requests
from urllib.parse import urlparse



def get_kaggle_files(cache_path, files, destination):
    if not os.path.exists(destination):
        os.makedirs(destination)

    for file_name in files:
        cached_file_path = os.path.join(cache_path, file_name)
        target_path = os.path.join(destination, file_name)

        if os.path.exists(cached_file_path):
            # Check if target already exists and delete it if it does
            if os.path.exists(target_path):
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)  # Remove existing directory
                else:
                    os.remove(target_path)  # Remove existing file

            if os.path.isfile(cached_file_path):
                # If it's a file, copy it
                shutil.copy(cached_file_path, target_path)
            elif os.path.isdir(cached_file_path):
                # If it's a directory, copy it recursively
                shutil.copytree(cached_file_path, target_path)
        else:
            raise EDAerror.Invalid_Directory (f"File or directory '{file_name}' not found in the cache.")

def remove_cache_data(cached_file_path):
    
    pattern = r'(.*\\datasets\\[^\\]+)\\'
    match = re.match(pattern, cached_file_path)

    if match:
        folder_path = match.group(1)
        shutil.rmtree(folder_path)

# Function to check if the Kaggle URL is accessible
def is_kaggle_url_valid(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True
        else:
            # Raise exception for invalid status codes
            raise EDAerror.InvalidInput(url, f"Failed to access Kaggle dataset at {url}. Status code: {response.status_code}")
    except requests.RequestException as e:
        # Raise exception for any request-related error
        raise EDAerror.InvalidInput(url, f"Error accessing the Kaggle dataset URL {url}: {e}")
    
def extract_kaggle_dataset_name(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    # The dataset name is the part after '/datasets/'
    dataset_name = path.split('/datasets/')[1] if '/datasets/' in path else None
    return dataset_name

def check_input_type(input_str):
    # Check if the input is a valid Kaggle URL
    if re.match(r'^(https?://)?(www\.)?kaggle\.com/datasets/.+', input_str):
        return 'URL'
    elif '/' in input_str:  
        return 'ID'
    else:
        return None
    