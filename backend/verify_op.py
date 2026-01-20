import json
import os
import sys

# Add backend to path for imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)
from media_cdn_api import get_access_token, make_gcp_request

def verify():
    root_dir = os.path.dirname(backend_dir)
    creds_path = os.path.join(root_dir, 'credentials', 'key.json')
    with open(creds_path, 'r') as f:
        key_data = json.load(f)
    
    token = get_access_token(key_data)
    op_name = "projects/your-project-id/locations/global/operations/your-operation-id"
    url = f"https://networkservices.googleapis.com/v1alpha1/{op_name}"
    
    print(f"Verifying API at: {url}")
    try:
        resp = make_gcp_request(url, token=token)
        print("\nSUCCESS! Response data:")
        print(json.dumps(resp, indent=2))
    except Exception as e:
        print("\nFAILED: Error Details:")
        print(str(e))

if __name__ == "__main__":
    verify()
