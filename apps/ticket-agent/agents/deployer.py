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
    """
    Deploys HTML to local nginx on the same server.
    Serves at http://<SERVER_IP>/concerts/<artist_slug>/
    """
    server_ip = os.environ.get("SERVER_IP", "91.99.126.231")
    web_root = Path("/var/www/concerts") / artist_slug
    web_root.mkdir(parents=True, exist_ok=True)

    # Copy HTML file
    shutil.copy2(html_path, web_root / "index.html")

    # Install and configure nginx if not already done
    _ensure_nginx()

    site_url = f"http://{server_ip}/concerts/{artist_slug}"
    return {
        "deployment_url": site_url,
        "subdomain_url": site_url,
        "provider": "nginx"
    }


def _ensure_nginx():
    """Install nginx and configure it to serve /var/www/concerts/ if not already set up."""
    nginx_conf = Path("/etc/nginx/sites-available/concerts")
    if not nginx_conf.exists():
        conf = """server {
    listen 80 default_server;
    server_name _;

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
        # Install nginx if missing
        if not shutil.which("nginx"):
            subprocess.run(["apt-get", "install", "-y", "-qq", "nginx"], check=True)

        nginx_conf.write_text(conf)
        enabled = Path("/etc/nginx/sites-enabled/concerts")
        if not enabled.exists():
            enabled.symlink_to(nginx_conf)

        # Disable default site
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
        resp = http.post(f"https://api.vercel.com/v13/deployments", headers=headers, json=payload)
        resp.raise_for_status()
        deployment = resp.json()

    url = f"https://{deployment['url']}"
    return {"deployment_url": url, "subdomain_url": url, "provider": "vercel"}


def deploy(html_path: str, artist_slug: str) -> dict:
    """Auto-selects provider based on available env vars."""
    if os.environ.get("VERCEL_TOKEN"):
        return deploy_to_vercel(html_path, artist_slug)
    elif os.environ.get("NETLIFY_TOKEN"):
        from .deployer_netlify import deploy_to_netlify
        return deploy_to_netlify(html_path, artist_slug)
    else:
        # Default: deploy to local nginx on same server
        return deploy_to_nginx(html_path, artist_slug)



def deploy_to_vercel(html_path: str, artist_slug: str) -> dict:
    """
    Deploys a single-file HTML site to Vercel.
    Returns {"url": "https://...", "subdomain": "artist-slug.yourdomain.com"}
    """
    token = os.environ["VERCEL_TOKEN"]
    project_name = f"concert-{artist_slug}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Read HTML
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Create deployment via Vercel API v13
    payload = {
        "name": project_name,
        "files": [
            {
                "file": "index.html",
                "data": html_content,
                "encoding": "utf-8"
            }
        ],
        "projectSettings": {
            "framework": None,
            "outputDirectory": "."
        },
        "target": "production"
    }

    with httpx.Client(timeout=60) as http:
        resp = http.post(
            f"{VERCEL_API}/v13/deployments",
            headers=headers,
            json=payload
        )
        resp.raise_for_status()
        deployment = resp.json()

    deployment_url = f"https://{deployment['url']}"

    # Add custom subdomain alias if BASE_DOMAIN is set
    base_domain = os.environ.get("BASE_DOMAIN")
    subdomain_url = None

    if base_domain and deployment.get("id"):
        subdomain = f"{artist_slug}.{base_domain}"
        alias_payload = {"alias": subdomain}

        with httpx.Client(timeout=30) as http:
            alias_resp = http.post(
                f"{VERCEL_API}/v2/deployments/{deployment['id']}/aliases",
                headers=headers,
                json=alias_payload
            )
            if alias_resp.status_code == 200:
                subdomain_url = f"https://{subdomain}"

    return {
        "deployment_url": deployment_url,
        "subdomain_url": subdomain_url or deployment_url,
        "deployment_id": deployment.get("id")
    }


def deploy_to_netlify(html_path: str, artist_slug: str) -> dict:
    """
    Alternative: deploy to Netlify as a zip.
    Returns {"url": "..."}
    """
    token = os.environ["NETLIFY_TOKEN"]

    with open(html_path, "rb") as f:
        html_bytes = f.read()

    # Create zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("index.html", html_bytes)
    zip_buffer.seek(0)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/zip"
    }

    with httpx.Client(timeout=60) as http:
        resp = http.post(
            "https://api.netlify.com/api/v1/sites",
            headers=headers,
            content=zip_buffer.read()
        )
        resp.raise_for_status()
        data = resp.json()

    site_url = data.get("ssl_url") or data.get("url")
    site_id = data.get("id")

    # Set custom subdomain
    base_domain = os.environ.get("BASE_DOMAIN")
    if base_domain and site_id:
        subdomain = f"{artist_slug}.{base_domain}"
        with httpx.Client(timeout=30) as http:
            http.put(
                f"https://api.netlify.com/api/v1/sites/{site_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"custom_domain": subdomain}
            )

    return {
        "deployment_url": site_url,
        "subdomain_url": f"https://{artist_slug}.{base_domain}" if base_domain else site_url,
        "site_id": site_id
    }


def deploy(html_path: str, artist_slug: str) -> dict:
    """Auto-selects provider based on available env vars."""
    if os.environ.get("VERCEL_TOKEN"):
        return deploy_to_vercel(html_path, artist_slug)
    elif os.environ.get("NETLIFY_TOKEN"):
        return deploy_to_netlify(html_path, artist_slug)
    else:
        raise EnvironmentError(
            "No deployment provider configured. Set VERCEL_TOKEN or NETLIFY_TOKEN in .env"
        )
