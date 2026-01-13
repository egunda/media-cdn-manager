import json
import os
import sys
from media_cdn_api import get_access_token, make_gcp_request, get_project_number

backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(backend_dir)
creds_path = os.path.join(root_dir, 'credentials', 'key.json')
with open(creds_path, 'r') as f:
    key_data = json.load(f)

project_id = key_data['project_id']
token = get_access_token(key_data)
project_number = get_project_number(project_id, token)
print(f"Project ID: {project_id}")
print(f"Project Number: {project_number}")
