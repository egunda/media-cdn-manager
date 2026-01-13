import json
import os
import sys

# Add backend to path for imports
sys.path.append('/Users/vivekanurag/.gemini/jetski/scratch/media-cdn-deployer/backend')
from media_cdn_api import get_access_token, make_gcp_request

def verify():
    creds_path = '/Users/vivekanurag/.gemini/jetski/scratch/media-cdn-deployer/credentials/key.json'
    with open(creds_path, 'r') as f:
        key_data = json.load(f)
    
    token = get_access_token(key_data)
    op_name = "projects/cdn-golden-demos/locations/global/operations/operation-1767980238626-647f7fa17e034-4f9df53b-d29b2ce2"
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
