"""
Deployer Agent — publishes the concert site to hosting.

Providers (auto-selected based on .env):
  1. Local nginx  — default, no config needed, serves from /var/www/concerts/
  2. Vercel       — set VERCEL_TOKEN
  3. Netlify      — set NETLIFY_TOKEN
"""
import os
import shutil
import subprocess
from pathlib import Path


def deploy_to_nginx(html_path: str, artist_slug: str) -> dict:
    server_ip = os.environ.get("SERVER_IP", "91.99.126.231")
    web_root = Path("/var/www/concerts") / artist_slug
    web_root.mkdir(parents=True, exist_ok=True)

    shutil.copy2(html_path, web_root / "index.html")
    _ensure_nginx()

    site_url = f"http://{server_ip}/concerts/{artist_slug}/"
    return {
        "deployment_url": site_url,
        "subdomain_url": site_url,
        "provider": "nginx"
    }


def _ensure_nginx():
    nginx_conf = Path("/etc/nginx/sites-available/concert")
    if not nginx_conf.exists():
        conf = """server {
    listen 80 default_server;
    server_name _;

    location /deploy {
        proxy_pass http://127.0.0.1:8080/deploy;
        proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;
        proxy_set_header Content-Type $content_type;
    }

    location /concerts/ {
        root /var/www;
        index index.html;
        try_files $uri $uri/ =404;
    }

    location / {
        root /var/www/html;
        index index.html;
    }
}"""
        if not shutil.which("nginx"):
            subprocess.run(["apt-get", "install", "-y", "-qq", "nginx"], check=True)

        nginx_conf.write_text(conf)
        enabled = Path("/etc/nginx/sites-enabled/concert")
        if not enabled.exists():
            enabled.symlink_to(nginx_conf)

        default = Path("/etc/nginx/sites-enabled/default")
        if default.exists():
            default.unlink()

        subprocess.run(["nginx", "-t"], check=True)
        subprocess.run(["systemctl", "reload", "nginx"], check=True)

    Path("/var/www/concerts").mkdir(parents=True, exist_ok=True)


def deploy_to_vercel(html_path: str, artist_slug: str) -> dict:
    import httpx
    token = os.environ["VERCEL_TOKEN"]
    project_name = f"concert-{artist_slug}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    payload = {
        "name": project_name,
        "files": [{"file": "index.html", "data": html_content, "encoding": "utf-8"}],
        "projectSettings": {"framework": None},
        "target": "production"
    }

    with httpx.Client(timeout=60) as http:
        resp = http.post("https://api.vercel.com/v13/deployments", headers=headers, json=payload)
        resp.raise_for_status()
        deployment = resp.json()

    url = f"https://{deployment['url']}"
    return {"deployment_url": url, "subdomain_url": url, "provider": "vercel"}


def deploy_to_netlify(html_path: str, artist_slug: str) -> dict:
    import httpx, io, zipfile
    token = os.environ["NETLIFY_TOKEN"]

    with open(html_path, "rb") as f:
        html_bytes = f.read()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("index.html", html_bytes)
    zip_buffer.seek(0)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/zip"}

    with httpx.Client(timeout=60) as http:
        resp = http.post("https://api.netlify.com/api/v1/sites", headers=headers, content=zip_buffer.read())
        resp.raise_for_status()
        data = resp.json()

    site_url = data.get("ssl_url") or data.get("url")
    return {"deployment_url": site_url, "subdomain_url": site_url, "provider": "netlify"}


def deploy(html_path: str, artist_slug: str) -> dict:
    """Auto-selects provider based on available env vars."""
    if os.environ.get("VERCEL_TOKEN"):
        return deploy_to_vercel(html_path, artist_slug)
    elif os.environ.get("NETLIFY_TOKEN"):
        return deploy_to_netlify(html_path, artist_slug)
    else:
        return deploy_to_nginx(html_path, artist_slug)
