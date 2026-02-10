import os
import sys
import secrets
import base64
import threading
import time
import http.server
import json
import http.cookies
import urllib.request
import urllib.parse

# Add the current directory to sys.path for local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from urllib.parse import urlparse, parse_qs
from media_cdn_api import (
    get_access_token, make_gcp_request, get_project_number, 
    check_bucket_iam, grant_bucket_iam, create_gcs_bucket,
    upload_gcs_object, list_gcs_object_versions, get_gcs_object_content
)

# In-memory job storage
jobs = {}

def get_system_bucket(project_number):
    """Resolves the system bucket name, favoring custom settings if available."""
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(backend_dir)
        settings_path = os.path.join(root_dir, 'credentials', 'settings.json')
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                if settings.get('bucket_name'):
                    return settings['bucket_name']
    except Exception as e:
        print(f"Error reading settings.json: {e}")
    
    # Default fallback
    return f"{project_number}-mediacdn-do-not-delete"

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        # Normalize path: remove query params and trailing slash
        path = self.path.split('?')[0].rstrip('/')
        if path == '': path = '/'


        if path == '/api/deploy':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            job_id = f"job_{int(time.time())}"
            jobs[job_id] = {
                "status": "Starting",
                "progress": 0,
                "logs": ["Job initiated..."]
            }
            
            # Start deployment in a background thread
            thread = threading.Thread(target=run_deployment_task, args=(job_id, payload))
            thread.start()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"job_id": job_id}).encode())
        elif path in ['/api/origin', '/api/origins']:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            job_id = f"origin_{int(time.time())}"
            jobs[job_id] = {
                "status": "Starting",
                "progress": 0,
                "logs": ["Origin creation initiated..."]
            }
            
            thread = threading.Thread(target=run_origin_task, args=(job_id, payload))
            thread.start()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"job_id": job_id}).encode())
        elif path == '/api/iam/grant-bucket':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))
                bucket_name = payload.get('bucket')
                print(f"GRANT IAM REQUEST: bucket={bucket_name}")
                
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                
                # 1. Ensure service identities exist
                for svc in ["mediaedgefill.googleapis.com", "mediaedge.googleapis.com"]:
                    try:
                        url_identity = f"https://serviceusage.googleapis.com/v1/projects/{project_id}/services/{svc}:generateServiceIdentity"
                        make_gcp_request(url_identity, method="POST", token=token)
                    except:
                        pass # Ignore if already exists or fails

                project_number = get_project_number(project_id, token)
                # Media CDN uses this service account to fetch content from origins (like GCS)
                service_accounts = [
                    f"service-{project_number}@gcp-sa-mediaedgefill.iam.gserviceaccount.com"
                ]
                # Best practice: objectViewer is for objects, legacyBucketReader is often needed for bucket traversal
                roles = ["roles/storage.objectViewer", "roles/storage.legacyBucketReader"]
                
                grant_bucket_iam(bucket_name, service_accounts, roles, token)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "Success"}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif path == '/api/staging/create':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))
                
                job_id = f"staging_{int(time.time())}"
                jobs[job_id] = {
                    "status": "Starting",
                    "progress": 0,
                    "logs": ["Staging creation initiated..."]
                }
                
                thread = threading.Thread(target=run_staging_task, args=(job_id, payload))
                thread.start()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"job_id": job_id}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif path == '/api/staging/promote':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))
                
                job_id = f"promote_{int(time.time())}"
                jobs[job_id] = {
                    "status": "Starting",
                    "progress": 0,
                    "logs": ["Promotion to production initiated..."]
                }
                
                thread = threading.Thread(target=run_promotion_task, args=(job_id, payload))
                thread.start()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"job_id": job_id}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            print(f"Unknown POST path: {path}")
            self.send_error(404)

    def do_DELETE(self):
        try:
            # Normalize path
            path = self.path.split('?')[0].rstrip('/')
            
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(backend_dir)
            creds_path = os.path.join(root_dir, 'credentials', 'key.json')
            with open(creds_path, 'r') as f:
                key_data = json.load(f)
            project_id = key_data['project_id']
            token = get_access_token(key_data)

            if path.startswith('/api/origin/'):
                origin_id = path.split('/')[-1]
                url = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheOrigins/{origin_id}"
                resp = make_gcp_request(url, method="DELETE", token=token)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            elif path.startswith('/api/service/'):
                service_id = path.split('/')[-1]
                url = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheServices/{service_id}"
                resp = make_gcp_request(url, method="DELETE", token=token)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            else:
                self.send_error(404)
        except Exception as e:
            print(f"Delete Error: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_GET(self):
        # Normalize path: remove query params and trailing slash
        path = self.path.split('?')[0].rstrip('/')
        if path == '': path = '/'
        
        # Public OAuth routes

        if path == '/api/config':
            try:
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    config_data = json.load(f)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(config_data).encode())
            except Exception as e:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif path == '/api/origins':
            try:
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                url = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheOrigins"
                resp = make_gcp_request(url, token=token)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif path == '/api/services':
            try:
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                url = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheServices"
                resp = make_gcp_request(url, token=token)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif path.startswith('/api/service/'):
            try:
                service_id = path.split('/')[-1]
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                url = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheServices/{service_id}"
                resp = make_gcp_request(url, token=token)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                status = 500
                if "404" in str(e):
                    status = 404
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif path.startswith('/api/origin/'):
            try:
                origin_id = path.split('/')[-1]
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                url = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheOrigins/{origin_id}"
                resp = make_gcp_request(url, token=token)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif path == '/api/buckets':
            try:
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                url = f"https://storage.googleapis.com/storage/v1/b?project={project_id}"
                resp = make_gcp_request(url, token=token)
                buckets = [{"name": b["name"]} for b in resp.get("items", [])]
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"buckets": buckets}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif path == '/api/secrets':
            try:
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                url = f"https://secretmanager.googleapis.com/v1/projects/{project_id}/secrets"
                resp = make_gcp_request(url, token=token)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif path == '/api/keysets':
            try:
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                url = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheKeysets"
                resp = make_gcp_request(url, token=token)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif path == '/api/certificates':
            try:
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                url = f"https://certificatemanager.googleapis.com/v1/projects/{project_id}/locations/global/certificates"
                resp = make_gcp_request(url, token=token)
                print(f"Listing SSL Certs Resp: {resp}")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif path.startswith('/api/status/'):
            job_id = path.split('/')[-1]
            if job_id in jobs:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(jobs[job_id]).encode())
            else:
                self.send_error(404)
        elif path == '/api/iam/check-bucket':
            try:
                query = parse_qs(urlparse(self.path).query)
                bucket_name = query.get('bucket', [None])[0]
                if not bucket_name:
                    raise Exception("Bucket name is required")
                
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                
                project_number = get_project_number(project_id, token)
                service_accounts = [
                    f"service-{project_number}@gcp-sa-mediaedgefill.iam.gserviceaccount.com"
                ]
                # Include broader roles that also grant the necessary permissions
                roles = ["roles/storage.objectViewer", "roles/storage.legacyBucketReader", "roles/storage.admin", "roles/viewer", "roles/editor", "roles/owner"]
                
                has_access = check_bucket_iam(bucket_name, service_accounts, roles, token)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "has_access": has_access,
                    "service_accounts": service_accounts,
                    "roles_checked": roles
                }).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif path == '/api/staging/versions':
            try:
                query = parse_qs(urlparse(self.path).query)
                service_id = query.get('service', [None])[0]
                if not service_id:
                    raise Exception("Service ID is required")
                
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(backend_dir)
                creds_path = os.path.join(root_dir, 'credentials', 'key.json')
                with open(creds_path, 'r') as f:
                    key_data = json.load(f)
                
                project_id = key_data['project_id']
                token = get_access_token(key_data)
                project_number = get_project_number(project_id, token)
                bucket_name = get_system_bucket(project_number)
                
                versions = []
                try:
                    raw_versions = list_gcs_object_versions(bucket_name, f"{service_id}.json", token)
                    for v in raw_versions:
                        try:
                            content = get_gcs_object_content(bucket_name, f"{service_id}.json", v["generation"], token)
                            config = json.loads(content)
                            versions.append({
                                "generation": v["generation"],
                                "updated": v["updated"],
                                "description": config.get("description", "No description provided")
                            })
                        except:
                            pass
                    versions.sort(key=lambda x: int(x["generation"]), reverse=True)
                except Exception as e:
                    print(f"Error listing versions: {e}")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"versions": versions}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            if path.startswith('/api/'):
                print(f"Unknown API path: {path}")
            super().do_GET()


def run_origin_task(job_id, payload):
    try:
        key_data = payload['key_data']
        project_id = payload['project_id']
        origin_name = payload['origin_name']
        origin_dns = payload['origin_dns']
        
        # Additional fields
        description = payload.get('description', '')
        protocol = payload.get('protocol', 'HTTPS')
        port = int(payload.get('port', 443))
        host_header = payload.get('host_header', '')
        
        jobs[job_id]["logs"].append("Authenticating...")
        token = get_access_token(key_data)
        jobs[job_id]["progress"] = 10
        
        jobs[job_id]["logs"].append(f"Creating Edge Cache Origin: {origin_name}...")
        url = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheOrigins?edgeCacheOriginId={origin_name}"
        origin_body = {
            "originAddress": origin_dns,
            "protocol": protocol,
            "port": port,
            "description": description
        }
        
        if host_header:
            origin_body["commonOverride"] = {
                "hostHeader": host_header
            }
        
        resp = make_gcp_request(url, method="POST", data=origin_body, token=token)
        operation_name = resp["name"]
        jobs[job_id]["logs"].append(f"Origin creation started. Operation: {operation_name}")
        
        start_time = time.time()
        while True:
            # Polling always uses the name returned, but we prefix with the version requested
            op_url = f"https://networkservices.googleapis.com/v1alpha1/{operation_name}"
            print(f"Polling operation: {op_url}")
            op_resp = make_gcp_request(op_url, token=token)
            if op_resp.get("done"):
                if op_resp.get("error"):
                    raise Exception(f"Origin creation failed: {op_resp['error']}")
                jobs[job_id]["logs"].append("Origin created successfully.")
                jobs[job_id]["progress"] = 100
                jobs[job_id]["status"] = "Success"
                break
            
            elapsed = int(time.time() - start_time)
            p = min(95, 10 + int((elapsed / 300) * 85))
            jobs[job_id].update({"progress": p, "status": f"Creating Origin ({elapsed}s)"})
            time.sleep(20)
            
    except Exception as e:
        jobs[job_id]["status"] = "Failed"
        jobs[job_id]["logs"].append(f"Error: {str(e)}")

def run_deployment_task(job_id, payload):
    try:
        key_data = payload['key_data']
        project_id = payload['project_id']
        origin_name = payload['origin_name']
        setup_name = payload['setup_name']
        original_json = payload.get('original_json')
        
        jobs[job_id]["logs"].append("Authenticating with Google Cloud...")
        token = get_access_token(key_data)
        jobs[job_id]["progress"] = 10
        
        origin_path = f"projects/{project_id}/locations/global/edgeCacheOrigins/{origin_name}"
        
        jobs[job_id]["logs"].append(f"Preparing Media CDN Service: {setup_name}...")
        url = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheServices?edgeCacheServiceId={setup_name}"
        
        if original_json:
            jobs[job_id]["logs"].append("High-fidelity clone mode: Preserving original configuration rules and headers.")
            service_body = original_json
            # Strip read-only or project-specific fields to avoid conflicts
            for field in ["updateTime", "createTime", "etag", "ipv4Addresses", "ipv6Addresses", "name"]:
                service_body.pop(field, None)
            
            # Update Hosts (Domain)
            if "routing" in service_body and "hostRules" in service_body["routing"]:
                for hr in service_body["routing"]["hostRules"]:
                    hr["hosts"] = [payload['domain']]
            
            # Update SSL Certificates
            if payload.get('ssl_certificate'):
                service_body["edgeSslCertificates"] = [payload['ssl_certificate']]
            else:
                service_body.pop("edgeSslCertificates", None)
            
            # Intelligent Origin Update: Only update origins that match the 'main' origin from UI selection 
            # if we can detect one, or if they were explicitly changed.
            # In simple high-fidelity clone, we'll keep all origins as is UNLESS we want to force the UI selection.
            # For now, let's keep original origins to maintain high fidelity, but if the user wants to change it 
            # we might need more logic. Let's force the UI-selected origin for the first rule at least.
            if "routing" in service_body and "pathMatchers" in service_body["routing"]:
                for pm in service_body["routing"]["pathMatchers"]:
                    for i, rule in enumerate(pm.get("routeRules", [])):
                        # If this is the primary rule (priority 1) and we have a UI origin selected, use it.
                        if i == 0 or rule.get("priority") == "1":
                             rule["origin"] = origin_path
        else:
            # Helper for Dual Token logic
            dual_token = payload.get('dual_token_config', {})
            enable_dual_token = dual_token.get('enabled', False)
            
            short_keyset = dual_token.get('short_keyset')
            long_keyset = dual_token.get('long_keyset')

            if enable_dual_token:
                jobs[job_id]["logs"].append(f"Applying Dual Token Protection (Short: {short_keyset}, Long: {long_keyset})...")

            def get_route(desc, pattern, default_ttl, priority, mode="FORCE_CACHE_ALL", client_ttl="1s", security_type=None):
                cdn_policy = {
                    "cacheMode": mode,
                    "defaultTtl": default_ttl,
                    "clientTtl": client_ttl,
                    "cacheKeyPolicy": {},
                    "signedRequestMode": "DISABLED"
                }

                if enable_dual_token:
                    sig_algo = dual_token.get('signature_algorithm', 'HMAC_SHA_256')
                    is_hmac = sig_algo.startswith('HMAC')

                    if security_type == "MASTER":
                        cdn_policy.update({
                            "signedRequestMode": "REQUIRE_TOKENS",
                            "signedRequestKeyset": f"projects/{project_id}/locations/global/edgeCacheKeysets/{short_keyset}",
                            "signedRequestMaximumExpirationTtl": "3600s",
                            "addSignatures": {
                                "actions": ["GENERATE_TOKEN_HLS_COOKIELESS"],
                                "keyset": f"projects/{project_id}/locations/global/edgeCacheKeysets/{long_keyset}",
                                "tokenQueryParameter": "hdntl",
                                "tokenTtl": "86400s",
                                "copiedParameters": ["data", "Data", "Headers", "PathGlobs", "SessionID", "URLPrefix"]
                            },
                            "signedTokenOptions": {
                                "tokenQueryParameter": "hdnts",
                                "allowedSignatureAlgorithms": [sig_algo]
                            }
                        })
                    elif security_type == "CHILD":
                        use_short = dual_token.get('child_use_short_token', False)
                        ks_to_use = short_keyset if use_short else long_keyset
                        token_param = "hdnts" if use_short else "hdntl"
                        
                        sto = {"tokenQueryParameter": token_param}
                        if not is_hmac:
                            sto["allowedSignatureAlgorithms"] = [sig_algo]
                            
                        cdn_policy.update({
                            "signedRequestMode": "REQUIRE_TOKENS",
                            "signedRequestKeyset": f"projects/{project_id}/locations/global/edgeCacheKeysets/{ks_to_use}",
                            "addSignatures": {
                                "actions": ["PROPAGATE_TOKEN_HLS_COOKIELESS"],
                                "tokenQueryParameter": "hdntl"
                            },
                            "signedTokenOptions": sto
                        })
                    elif security_type == "SEGMENT":
                        sto = {"tokenQueryParameter": "hdntl"}
                        if not is_hmac:
                            sto["allowedSignatureAlgorithms"] = [sig_algo]
                            
                        cdn_policy.update({
                            "signedRequestMode": "REQUIRE_TOKENS",
                            "signedRequestKeyset": f"projects/{project_id}/locations/global/edgeCacheKeysets/{long_keyset}",
                            "signedTokenOptions": sto
                        })
                    
                return {
                    "description": desc,
                    "priority": priority,
                    "origin": origin_path,
                    "matchRules": [{"pathTemplateMatch": pattern, "ignoreCase": True}],
                    "routeAction": {
                        "cdnPolicy": cdn_policy,
                        "corsPolicy": {
                            "allowOrigins": ["*"], 
                            "allowMethods": ["*"], 
                            "allowHeaders": ["*"],
                            "exposeHeaders": ["*"], 
                            "maxAge": "600s", 
                            "allowCredentials": True
                        }
                    },
                    "routeMethods": {
                        "allowedMethods": ["GET", "HEAD", "OPTIONS"]
                    }
                }

            route_rules = []
            if payload['setup_type'] == "VOD":
                vod_ttl = "31536000s"
                route_rules.append(get_route("Master Manifest", "/**/manifest.m3u8", vod_ttl, "1", security_type="MASTER"))
                route_rules.append(get_route("Child Playlist", "/**.m3u8", vod_ttl, "2", security_type="CHILD"))
                route_rules.append(get_route("TS Chunks", "/**.ts", vod_ttl, "3", security_type="SEGMENT"))
                route_rules.append(get_route("DASH Manifest", "/**/manifest.mpd", vod_ttl, "47"))
                route_rules.append(get_route("DASH Segments (m4s)", "/**.m4s", vod_ttl, "48"))
                route_rules.append(get_route("DASH Segments (mp4)", "/**.mp4", vod_ttl, "49"))
                route_rules.append(get_route("All Other", "/**", vod_ttl, "100"))
            else:
                route_rules.append(get_route("Live Master Manifest", "/**/manifest.m3u8", "86400s", "1", security_type="MASTER"))
                route_rules.append(get_route("Live Child Playlist", "/**.m3u8", "2s", "2", security_type="CHILD"))
                route_rules.append(get_route("Live Media Chunks", "/**.ts", "31536000s", "3", security_type="SEGMENT"))
                route_rules.append(get_route("Live DASH Manifest", "/**/manifest.mpd", "2s", "47"))
                route_rules.append(get_route("Live DASH Segments (m4s)", "/**.m4s", "31536000s", "48"))
                route_rules.append(get_route("Live DASH Segments (mp4)", "/**.mp4", "31536000s", "49"))

            service_body = {
                "routing": {
                    "hostRules": [{"hosts": [payload['domain']], "pathMatcher": "path-matcher-0"}],
                    "pathMatchers": [{"name": "path-matcher-0", "routeRules": route_rules}]
                },
                "logConfig": {"enable": True, "sampleRate": 1.0}
            }

            if payload.get('ssl_certificate'):
                service_body["edgeSslCertificates"] = [payload['ssl_certificate']]

        jobs[job_id]["progress"] = 50
        resp = make_gcp_request(url, method="POST", data=service_body, token=token)
        operation_name = resp["name"]
        jobs[job_id]["logs"].append(f"Service deployment started. Operation: {operation_name}")
        
        start_time = time.time()
        while True:
            op_url = f"https://networkservices.googleapis.com/v1alpha1/{operation_name}"
            print(f"Polling operation: {op_url}")
            op_resp = make_gcp_request(op_url, token=token)
            if op_resp.get("done"):
                if op_resp.get("error"):
                    raise Exception(f"Service deployment failed: {op_resp['error']}")
                jobs[job_id]["logs"].append("Media CDN deployed successfully!")
                jobs[job_id]["progress"] = 100
                jobs[job_id]["status"] = "Success"
                break
            
            elapsed = int(time.time() - start_time)
            p = 50 + min(45, int((elapsed / 300) * 45))
            jobs[job_id].update({"progress": p, "status": f"Deploying ({elapsed}s)"})
            time.sleep(20)

    except Exception as e:
        jobs[job_id]["status"] = "Failed"
        jobs[job_id]["logs"].append(f"Error: {str(e)}")

def run_staging_task(job_id, payload):
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(backend_dir)
        creds_path = os.path.join(root_dir, 'credentials', 'key.json')
        with open(creds_path, 'r') as f:
            key_data = json.load(f)
        
        project_id = key_data['project_id']
        service_id = payload['service_id']
        staging_service_id = f"{service_id}-staging"
        bucket_region = payload.get('region', 'asia-south1') # Mumbai default
        
        jobs[job_id]["logs"].append(f"Starting cloning process for {service_id}...")
        token = get_access_token(key_data)
        project_number = get_project_number(project_id, token)
        bucket_name = get_system_bucket(project_number)
        
        # 0. Ensure GCS bucket exists early so user sees it
        jobs[job_id]["logs"].append(f"Ensuring GCS bucket {bucket_name} exists in {bucket_region}...")
        create_gcs_bucket(bucket_name, project_id, bucket_region, token)
        
        # 1. Fetch original service
        jobs[job_id]["logs"].append("Fetching original service configuration...")
        url_fetch = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheServices/{service_id}"
        original_service = make_gcp_request(url_fetch, token=token)
        
        # 2. Prepare staging config
        jobs[job_id]["logs"].append(f"Preparing staging config: {staging_service_id}...")
        staging_body = original_service.copy()
        for field in ["updateTime", "createTime", "etag", "ipv4Addresses", "ipv6Addresses", "name"]:
            staging_body.pop(field, None)
        
        # Update description if needed (user might want version notes)
        staging_body["description"] = payload.get("description", f"Staging for {service_id}")
        
        # 3. Deploy staging
        jobs[job_id]["logs"].append(f"Deploying staging service...")
        url_deploy = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheServices?edgeCacheServiceId={staging_service_id}"
        
        try:
            # Check if staging already exists, if so update it
            url_check = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheServices/{staging_service_id}"
            make_gcp_request(url_check, token=token)
            jobs[job_id]["logs"].append("Staging service already exists. Updating...")
            url_deploy = f"{url_check}?updateMask=routing,logConfig,edgeSslCertificates,description"
            resp = make_gcp_request(url_deploy, method="PATCH", data=staging_body, token=token)
        except:
            # Create new
            resp = make_gcp_request(url_deploy, method="POST", data=staging_body, token=token)
            
        operation_name = resp["name"]
        jobs[job_id]["logs"].append(f"Operation started: {operation_name}")
        
        start_time = time.time()
        while True:
            op_url = f"https://networkservices.googleapis.com/v1alpha1/{operation_name}"
            op_resp = make_gcp_request(op_url, token=token)
            if op_resp.get("done"):
                if op_resp.get("error"):
                    raise Exception(f"Deployment failed: {op_resp['error']}")
                break
            
            elapsed = int(time.time() - start_time)
            p = min(80, 10 + int((elapsed / 300) * 70))
            jobs[job_id].update({"progress": p, "status": f"Deploying Staging ({elapsed}s)"})
            time.sleep(20)

        # 4. Sync YAML to GCS
        jobs[job_id]["logs"].append(f"Syncing configuration to GCS with versioning...")
        upload_gcs_object(bucket_name, f"{service_id}.json", staging_body, token)
        
        # Also sync other YAMLs in sample-configs if requested?
        # "Sync all the yaml in this directory"
        # Let's assume this means the sample-configs for now as a baseline
        sample_dir = os.path.join(root_dir, "sample-configs")
        if os.path.exists(sample_dir):
            for filename in os.listdir(sample_dir):
                if filename.endswith(".yaml"):
                    try:
                        with open(os.path.join(sample_dir, filename), "r") as f:
                            content = f.read()
                        upload_gcs_object(bucket_name, filename, content, token, content_type="text/plain")
                    except:
                        pass

        jobs[job_id]["progress"] = 100
        jobs[job_id]["status"] = "Success"
        jobs[job_id]["logs"].append("Staging environment created and synced successfully!")
        
    except Exception as e:
        jobs[job_id]["status"] = "Failed"
        jobs[job_id]["logs"].append(f"Error: {str(e)}")

def run_promotion_task(job_id, payload):
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(backend_dir)
        creds_path = os.path.join(root_dir, 'credentials', 'key.json')
        with open(creds_path, 'r') as f:
            key_data = json.load(f)
        
        project_id = key_data['project_id']
        service_id = payload['service_id'] # target production service
        staging_service_id = f"{service_id}-staging"
        generation = payload.get('generation') # optional: promote specific version
        
        token = get_access_token(key_data)
        
        # 1. Fetch config to promote
        if generation:
            jobs[job_id]["logs"].append(f"Promoting version {generation} to production...")
            project_number = get_project_number(project_id, token)
            bucket_name = get_system_bucket(project_number)
            promote_config = json.loads(get_gcs_object_content(bucket_name, f"{service_id}.json", generation, token))
        else:
            jobs[job_id]["logs"].append(f"Promoting current staging config to production...")
            url_fetch = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheServices/{staging_service_id}"
            promote_config = make_gcp_request(url_fetch, token=token)
        
        # 2. Prepare production config (strip fields)
        for field in ["updateTime", "createTime", "etag", "ipv4Addresses", "ipv6Addresses", "name"]:
            promote_config.pop(field, None)
            
        # 3. Deploy to production
        jobs[job_id]["logs"].append(f"Updating production service {service_id}...")
        url_update = f"https://networkservices.googleapis.com/v1alpha1/projects/{project_id}/locations/global/edgeCacheServices/{service_id}?updateMask=routing,logConfig,edgeSslCertificates,description"
        
        resp = make_gcp_request(url_update, method="PATCH", data=promote_config, token=token)
        operation_name = resp["name"]
        
        start_time = time.time()
        while True:
            op_url = f"https://networkservices.googleapis.com/v1alpha1/{operation_name}"
            op_resp = make_gcp_request(op_url, token=token)
            if op_resp.get("done"):
                if op_resp.get("error"):
                    raise Exception(f"Promotion failed: {op_resp['error']}")
                break
            
            elapsed = int(time.time() - start_time)
            p = min(100, 10 + int((elapsed / 300) * 90))
            jobs[job_id].update({"progress": p, "status": f"Promoting ({elapsed}s)"})
            time.sleep(20)

        jobs[job_id]["progress"] = 100
        jobs[job_id]["status"] = "Success"
        jobs[job_id]["logs"].append("Production environment updated successfully!")
        
    except Exception as e:
        jobs[job_id]["status"] = "Failed"
        jobs[job_id]["logs"].append(f"Error: {str(e)}")


def run_server(port=6001):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, RequestHandler)
    print(f"Starting server on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
