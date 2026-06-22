# Angetic Essence — Production Deployment

## Step 1: VPS Setup

```bash
# From your local machine, SCP the deploy package and license server:
scp -r deploy license_server root@YOUR_VPS_IP:/tmp/

# SSH into the VPS:
ssh root@YOUR_VPS_IP

# Run the deployment script:
sudo bash /tmp/deploy/deploy.sh
```

## Step 2: Stripe Products

1. Log into [Stripe Dashboard](https://dashboard.stripe.com)
2. Go to **Products** → **Add Product**

### Product 1: Perpetual License
- **Name:** Angetic Essence — Perpetual
- **Description:** One-time purchase, lifetime license
- **Pricing:** Standard price → $499.00 one-time
- Save, **copy the `price_xxx` ID**

### Product 2: Commercial Subscription
- **Name:** Angetic Essence — Commercial
- **Description:** Monthly subscription with updates
- **Pricing:** Recurring → $49.00/month
- Save, **copy the `price_xxx` ID**

## Step 3: Configure .env

```bash
sudo nano /opt/angetic-license/.env
```

Set the values:

```ini
STRIPE_SECRET_KEY=sk_live_YOUR_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET
ADMIN_API_KEY=<openssl rand -hex 32>
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
```

## Step 4: Update Price IDs

Edit `license_server/app.py` and replace the `SUBSCRIPTION_TIERS` dictionary keys with your real Stripe price IDs.

## Step 5: Stripe Webhook

1. Stripe Dashboard → **Developers** → **Webhooks** → **Add endpoint**
2. URL: `https://api.angeticessence.com/stripe-webhook`
3. Events: `checkout.session.completed`, `invoice.payment_failed`
4. Copy the **Signing Secret** → paste into `.env` as `STRIPE_WEBHOOK_SECRET`

## Step 6: Restart & Verify

```bash
sudo systemctl restart license-server
sudo systemctl status license-server
curl https://api.angeticessence.com/health
```

## File Reference

| Path | Purpose |
|------|---------|
| `/opt/angetic-license/.env` | Secrets (SMTP, Stripe, admin key) |
| `/opt/angetic-license/license_server/` | Flask app package |
| `/var/log/angetic/` | Gunicorn access + error logs |
| `/etc/nginx/sites-available/api.angeticessence.com` | Nginx reverse proxy |
| `/etc/systemd/system/license-server.service` | systemd service unit |
