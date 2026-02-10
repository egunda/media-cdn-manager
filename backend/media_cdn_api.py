import time
import socket
import json
import base64
import urllib.request
import urllib.parse
import subprocess
import tempfile
import os

# Project Number Cache
_PROJECT_NUMBER_CACHE = {}

def b64_encode(data):
    if isinstance(data, dict):
        data = json.dumps(data).encode()
    elif isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def get_access_token(service_account_info):
    """Generates an access token using openssl CLI for signing."""
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": service_account_info["client_email"],
        "sub": service_account_info["client_email"],
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
        "scope": "https://www.googleapis.com/auth/cloud-platform"
    }

    signing_input = f"{b64_encode(header)}.{b64_encode(payload)}"
    
    # Use OpenSSL to sign
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(service_account_info["private_key"])
        key_path = f.name
    
    try:
        # Sign the input
        process = subprocess.Popen(
            ["openssl", "dgst", "-sha256", "-sign", key_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        signature, stderr = process.communicate(input=signing_input.encode())
        
        if process.returncode != 0:
            raise Exception(f"OpenSSL Error: {stderr.decode()}")
            
        b64_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        jwt = f"{signing_input}.{b64_signature}"

        # Exchange JWT for Token
        data = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt
        }).encode()

        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
        with urllib.request.urlopen(req, timeout=10) as f_req:
            resp = json.loads(f_req.read().decode())
            return resp["access_token"]
    finally:
        if os.path.exists(key_path):
            os.remove(key_path)

def make_gcp_request(url, method="GET", data=None, token=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    encoded_data = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as f:
            content = f.read().decode()
            if not content:
                return {}
            return json.loads(content)
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode()
        if e.code == 409:
             raise Exception("GCP API Error: Resource already exists (409)")
        raise Exception(f"GCP API Error: {e.code} - {error_msg}")
    except (urllib.error.URLError, socket.timeout) as e:
        raise Exception(f"Network Error (Timeout/Connection): {str(e)}")

def get_project_number(project_id, token):
    if project_id in _PROJECT_NUMBER_CACHE:
        return _PROJECT_NUMBER_CACHE[project_id]
        
    url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}"
    resp = make_gcp_request(url, token=token)
    num = resp.get("projectNumber")
    if num:
        _PROJECT_NUMBER_CACHE[project_id] = num
    return num

def check_bucket_iam(bucket_name, service_accounts, roles, token):
    """Checks if any of the service accounts have any of the roles on a bucket."""
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/iam"
    policy = make_gcp_request(url, token=token)
    
    for binding in policy.get("bindings", []):
        if binding.get("role") in roles:
            for sa in service_accounts:
                member = f"serviceAccount:{sa}"
                if member in binding.get("members", []):
                    return True
    return False

def grant_bucket_iam(bucket_name, service_accounts, roles, token):
    """Grants multiple roles to multiple service accounts on a bucket."""
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/iam"
    policy = make_gcp_request(url, token=token)
    
    for role in roles:
        found_role = False
        for binding in policy.get("bindings", []):
            if binding.get("role") == role:
                for sa in service_accounts:
                    member = f"serviceAccount:{sa}"
                    if member not in binding.get("members", []):
                        binding.setdefault("members", []).append(member)
                found_role = True
                break
        
        if not found_role:
            policy.setdefault("bindings", []).append({
                "role": role,
                "members": [f"serviceAccount:{sa}" for sa in service_accounts]
            })
    
    # Set the updated policy
    return make_gcp_request(url, method="PUT", data=policy, token=token)

def create_gcs_bucket(bucket_name, project_id, location, token):
    """Creates a GCS bucket with versioning enabled."""
    url = f"https://storage.googleapis.com/storage/v1/b?project={project_id}"
    body = {
        "name": bucket_name,
        "location": location,
        "versioning": {"enabled": True}
    }
    try:
        return make_gcp_request(url, method="POST", data=body, token=token)
    except Exception as e:
        if "already exists" in str(e).lower():
            # If already exists, ensure versioning is enabled
            url_patch = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}"
            patch_body = {"versioning": {"enabled": True}}
            return make_gcp_request(url_patch, method="PATCH", data=patch_body, token=token)
        raise e

def upload_gcs_object(bucket_name, object_name, data, token, content_type="application/json"):
    """Uploads an object to GCS."""
    # Simple upload (not resumable for small configs)
    url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={object_name}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type
    }
    
    if isinstance(data, dict):
        encoded_data = json.dumps(data, indent=2).encode()
    else:
        encoded_data = data.encode() if isinstance(data, str) else data

    req = urllib.request.Request(url, data=encoded_data, headers=headers, method="POST")
    
    with urllib.request.urlopen(req, timeout=10) as f:
        return json.loads(f.read().decode())

def list_gcs_object_versions(bucket_name, object_name, token):
    """Lists all versions (generations) of an object."""
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o?versions=true&prefix={object_name}"
    resp = make_gcp_request(url, token=token)
    items = resp.get("items", [])
    # Filter exactly for the object name because prefix might match multiple
    versions = [item for item in items if item["name"] == object_name]
    return versions

def get_gcs_object_content(bucket_name, object_name, generation, token):
    """Gets the content of a specific version of an object."""
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o/{object_name}?alt=media&generation={generation}"
    headers = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as f:
        return f.read().decode()
