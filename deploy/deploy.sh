#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  Angetic Essence — License Server VPS Deployment Script
#  Tested on: Ubuntu 22.04 / 24.04
#  Usage: scp -r license_server/ deploy/ user@vps:/tmp/
#         ssh user@vps "sudo bash /tmp/deploy/deploy.sh"
# ============================================================

DOMAIN="${DOMAIN:-api.angeticessence.com}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@angeticessence.com}"

echo "============================================================"
echo "  Angetic Essence License Server — VPS Deployment"
echo "  Domain: $DOMAIN"
echo "============================================================"

# ---- Prerequisites ----
if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] Please run as root (sudo)"
    exit 1
fi

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"

# ---- Step 1: System dependencies ----
echo ""
echo "[1/8] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# ---- Step 2: Create application directory ----
echo ""
echo "[2/8] Creating application directory..."
INSTALL_DIR="/opt/angetic-license"
mkdir -p "$INSTALL_DIR"
mkdir -p /var/log/angetic

# Copy license_server package
echo "[3/8] Copying license server files..."
cp -r "$SCRIPT_DIR/../license_server" "$INSTALL_DIR/license_server"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/.env.production" "$INSTALL_DIR/.env"

# ---- Step 4: Python virtual environment ----
echo ""
echo "[4/8] Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
pip install -q -r "$INSTALL_DIR/requirements.txt"
deactivate

# ---- Step 5: Systemd service ----
echo ""
echo "[5/8] Installing systemd service..."
cp "$SCRIPT_DIR/license-server.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable license-server

# ---- Step 6: Nginx configuration ----
echo ""
echo "[6/8] Configuring Nginx..."
cp "$SCRIPT_DIR/nginx.conf" /etc/nginx/sites-available/$DOMAIN
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
fi
if [ ! -L /etc/nginx/sites-enabled/$DOMAIN ]; then
    ln -s /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
fi

# ---- Step 7: SSL via Certbot ----
echo ""
echo "[7/8] Obtaining SSL certificate..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $ADMIN_EMAIL || {
    echo "[WARN] Certbot failed — the server will still work on HTTP."
    echo "[WARN] Run manually: sudo certbot --nginx -d $DOMAIN"
}

# ---- Step 8: Start services ----
echo ""
echo "[8/8] Starting services..."
systemctl restart nginx
systemctl start license-server

# ---- Done ----
echo ""
echo "============================================================"
echo "  DEPLOYMENT COMPLETE"
echo "============================================================"
echo ""
echo "  IMPORTANT: You MUST edit the .env file:"
echo "    sudo nano $INSTALL_DIR/.env"
echo ""
echo "  Fill in:"
echo "    - STRIPE_SECRET_KEY"
echo "    - STRIPE_WEBHOOK_SECRET"
echo "    - SMTP credentials (for email delivery)"
echo "    - ADMIN_API_KEY (generate a random 64-char hex string)"
echo ""
echo "  Then restart the service:"
echo "    sudo systemctl restart license-server"
echo ""
echo "  Verify health:"
echo "    curl https://$DOMAIN/health"
echo ""
echo "  View logs:"
echo "    sudo journalctl -u license-server -f"
echo "    tail -f /var/log/angetic/error.log"
echo ""
echo "============================================================"
