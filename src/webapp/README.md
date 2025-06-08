# Drippy web dashboard

A tiny Flask app that reads the **`drippy.db`** SQLite database on your Raspberry Pi Zero 2 W, calculates 24-hour rainfall, and serves:

* `/api/latest` — JSON of the newest sensor values  
* `/` — a Bootstrap dashboard that refreshes every minute

The site is published through a **Cloudflare Tunnel**, so no inbound ports are opened on your router.

## Prerequisites

* Raspberry Pi Zero 2 W running Debian 12 (“bookworm”)
* Python ≥ 3.11
* Local MQTT → SQLite logger writing to `~/drippy.db`
* A Cloudflare-managed domain (e.g. `petalsbypedal.com`)
* Outbound internet on 443/TCP (for the tunnel) and 53/UDP, 123/UDP

--------------------------------------------------------------------
## Quick-start (development)

```bash
# clone the repo
mkdir -p ~/drippy/src && cd ~/drippy/src
git clone <your-repo-url> webapp && cd webapp

# python venv
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt

# run it locally
python app.py      # visit http://<pi-ip>:5000/ in a browser
```

## Production setup
### 1. Flask service
Create /etc/systemd/system/webapp.service

```ini
[Unit]
Description=Petals Flask Web App
After=network.target

[Service]
User=username
WorkingDirectory=/home/username/drippy/src/webapp
ExecStart=/home/username/drippy/src/webapp/env/bin/python app.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```


```bash
sudo systemctl daemon-reload
sudo systemctl enable --now webapp
The API is now on http://localhost:5000.
```

### 2. Cloudflare Tunnel (zero-trust HTTPS)
```bash
# one-time binary install (armv7)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm \
     -o cloudflared && chmod +x cloudflared && sudo mv cloudflared /usr/local/bin/

# auth (prints a URL—open on any logged-in device)
cloudflared tunnel login

# create & name tunnel
cloudflared tunnel create drippy

# DNS route (pick any easy sub-domain)
cloudflared tunnel route dns drippy data.petalsbypedal.com
Config file /etc/cloudflared/config.yml
```

```yaml
tunnel: drippy
credentials-file: /etc/cloudflared/drippy.json

ingress:
  - hostname: data.petalsbypedal.com
    service: http://localhost:5000
  - service: http_status:404
Install as a service:

```bash
sudo cloudflared --config /etc/cloudflared/config.yml service install
sudo systemctl status cloudflared  # should be active
```
Browse to https://data.petalsbypedal.com — public, TLS-encrypted, no router changes.


## Updating
Task | Command
-- | --
Pull code & restart Flask | `git pull && sudo systemctl restart webapp`
Upgrade Python deps	| `source env/bin/activate && pip install -U -r requirements.txt`
Update static assets | edit files then bump `?v=` query in `<script>` tag
Update cloudflared binary | re-download, then `sudo systemctl restart cloudflared`


## Security hardening (recommended)
```bash
sudo apt install ufw fail2ban unattended-upgrades -y
sudo ufw default deny incoming
sudo ufw allow out 53,80,443,123/tcp
sudo ufw enable
sudo systemctl enable --now fail2ban
sudo dpkg-reconfigure --priority=low unattended-upgrades
```
