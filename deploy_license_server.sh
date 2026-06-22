#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  Angetic Essence — License Server (Free-Tier Ubuntu)
#  Deploys Flask + Gunicorn behind Nginx reverse proxy
#  Tested on: Google Cloud e2-micro, AWS t2.micro, $5 DigitalOcean
#
#  Usage:
#    1. scp -r license_server/ user@<VPS_IP>:/tmp/
#    2. scp deploy_license_server.sh user@<VPS_IP>:/tmp/
#    3. ssh user@<VPS_IP>
#    4. sudo bash /tmp/deploy_license_server.sh
# ============================================================

DOMAIN="${DOMAIN:-api.angeticessence.com}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@angeticessence.com}"
APP_DIR="/opt/angetic-license"

if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] Run as root: sudo bash $0"
    exit 1
fi

cd "$(dirname "$0")"

echo "============================================================"
echo "  Angetic Essence License Server — Free-Tier Deployment"
echo "  Target: $DOMAIN"
echo "============================================================"

# ── Step 1: System ──
echo ""
echo "[1/6] Updating system and installing dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# ── Step 2: Application directory ──
echo ""
echo "[2/6] Setting up application directory..."
mkdir -p "$APP_DIR"
mkdir -p /var/log/angetic

# Copy license_server files from /tmp
cp -r /tmp/license_server "$APP_DIR/license_server"

# ── Step 3: Python venv + deps ──
echo ""
echo "[3/6] Creating Python virtual environment..."
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"
pip install -q flask gunicorn stripe cryptography pyyaml
deactivate

# ── Step 4: systemd service ──
echo ""
echo "[4/6] Creating systemd service..."
cat > /etc/systemd/system/license_server.service << 'SERVICE'
[Unit]
Description=Angetic Essence License Server
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/angetic-license
EnvironmentFile=/opt/angetic-license/.env
ExecStart=/opt/angetic-license/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8080 \
    --timeout 120 \
    --access-logfile /var/log/angetic/access.log \
    --error-logfile /var/log/angetic/error.log \
    license_server.app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable license_server

# ── Step 5: Nginx reverse proxy ──
echo ""
echo "[5/6] Configuring Nginx reverse proxy..."
cat > /etc/nginx/sites-available/$DOMAIN << 'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /stripe-webhook {
        proxy_pass http://127.0.0.1:8080/stripe-webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120;
    }

    location /health {
        proxy_pass http://127.0.0.1:8080/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX

rm -f /etc/nginx/sites-enabled/default
if [ ! -L /etc/nginx/sites-enabled/$DOMAIN ]; then
    ln -s /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
fi

# ── Step 6: Start services ──
echo ""
echo "[6/6] Starting services..."
systemctl restart nginx
systemctl start license_server

# ── Done ──
echo ""
echo "============================================================"
echo "  LICENSE SERVER DEPLOYED"
echo "============================================================"
echo ""
echo "  IMPORTANT: Configure your environment:"
echo "    sudo nano $APP_DIR/.env"
echo ""
echo "  Set these values:"
echo "    STRIPE_SECRET_KEY=sk_live_..."
echo "    STRIPE_WEBHOOK_SECRET=whsec_..."
echo "    ADMIN_API_KEY=\$(openssl rand -hex 32)"
echo "    SMTP_HOST=smtp.gmail.com"
echo "    SMTP_PORT=587"
echo "    SMTP_USER=your-email@gmail.com"
echo "    SMTP_PASS=your-app-password"
echo "    SMTP_FROM=licenses@angeticessence.com"
echo ""
echo "  Then restart the service:"
echo "    sudo systemctl restart license_server"
echo ""
echo "  Verify it's running:"
echo "    curl http://127.0.0.1:8080/health"
echo "    -> {\"status\": \"ok\", \"service\": \"license-server\"}"
echo ""
echo "  ─────────────────────────────────────────────"
echo "  SSL CERTIFICATE (required for Stripe webhooks)"
echo "  ─────────────────────────────────────────────"
echo ""
echo "  Point your domain's A record to this server's IP,"
echo "  then run:"
echo ""
echo "    sudo certbot --nginx -d $DOMAIN"
echo ""
echo "  Stripe will NOT send webhooks to an HTTP endpoint."
echo "  SSL must be configured before webhooks work."
echo ""
echo "============================================================"
