"""Automated email delivery for license keys via SMTP."""

import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"


def _load_config() -> dict:
    config = {
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "smtp_user": os.environ.get("SMTP_USER", ""),
        "smtp_pass": os.environ.get("SMTP_PASS", ""),
        "smtp_from": os.environ.get("SMTP_FROM", "licenses@angeticessence.com"),
        "site_url": os.environ.get("SITE_URL", "https://angeticessence.com"),
    }

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip().lower()
            val = val.strip().strip("\"'")
            if key == "smtp_host":
                config["smtp_host"] = val
            elif key == "smtp_port":
                config["smtp_port"] = int(val)
            elif key == "smtp_user":
                config["smtp_user"] = val
            elif key == "smtp_pass":
                config["smtp_pass"] = val
            elif key == "smtp_from":
                config["smtp_from"] = val
            elif key == "site_url":
                config["site_url"] = val

    return config


def send_license_email(
    to_email: str,
    license_key: str,
    tier: str,
    customer_name: str = "",
) -> bool:
    cfg = _load_config()

    if not cfg["smtp_host"] or not cfg["smtp_user"]:
        print(f"[EMAILER] SMTP not configured — would send to {to_email}")
        print(f"[EMAILER]   License key: {license_key}")
        print(f"[EMAILER]   Tier: {tier}")
        return False

    tier_labels = {
        "perpetual": "Perpetual License",
        "subscription_monthly": "Monthly Subscription",
        "subscription_yearly": "Annual Subscription",
    }
    tier_label = tier_labels.get(tier, tier)

    greeting = f"Hello {customer_name}," if customer_name else "Hello,"

    body = f"""
{greeting}

Thank you for purchasing Angetic Essence!

Your license key is below. Keep it private — it is tied to your account.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LICENSE KEY: {license_key}

TIER: {tier_label}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To activate:
1. Open config.yaml in your Angetic Essence installation directory
2. Set the license.key field to the key above
3. Restart the application

For documentation: {cfg["site_url"]}/docs

If you did not purchase this license, please contact us immediately at security@angeticessence.com.

— Angetic Essence Inc.
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your Angetic Essence License Key ({tier_label})"
    msg["From"] = cfg["smtp_from"]
    msg["To"] = to_email
    msg.attach(MIMEText(body.strip(), "plain"))

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=30) as server:
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_pass"])
            server.send_message(msg)
        print(f"[EMAILER] License sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAILER] Failed to send to {to_email}: {e}")
        return False
