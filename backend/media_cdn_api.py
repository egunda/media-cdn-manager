import time
import json
import base64
import urllib.request
import urllib.parse
import subprocess
import tempfile
import os

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
        with urllib.request.urlopen(req) as f_req:
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
        with urllib.request.urlopen(req) as f:
            return json.loads(f.read().decode())
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode()
        # Handle "already exists" specifically
        if e.code == 409: # Conflict
             raise Exception(f"GCP API Error: Resource already exists (409)")
        raise Exception(f"GCP API Error: {e.code} - {error_msg}")

def get_project_number(project_id, token):
    url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}"
    resp = make_gcp_request(url, token=token)
    return resp.get("projectNumber")

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
