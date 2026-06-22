"""License validation server — Stripe webhooks, key generation, validation API."""

import os
import json
import time
import hmac
import hashlib
from pathlib import Path

from flask import Flask, request, jsonify

from license_server.crypto import sign_license, verify_license, generate_key_pair
from license_server.key_store import (
    init_db,
    store_license,
    validate_key,
    log_validation,
    get_license_by_email,
    revoke_key,
    get_all_licenses,
)
from license_server.emailer import send_license_email

app = Flask(__name__)

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "change-me-in-production")

PERPETUAL_EXPIRY = 4102444800  # year 2099
SUBSCRIPTION_TIERS = {
    # ⚠️  REPLACE with your real Stripe price IDs from the Dashboard.
    #     Create 2 products:
    #       1. "Angetic Essence — Perpetual"  one-time $499  → copy price_xxx
    #       2. "Angetic Essence — Commercial"  recurring $49/mo  → copy price_xxx
    #     Then paste the IDs below:
    #
    # "price_live_xxxxxxxxxxxxxxxxxxxx": "perpetual",
    # "price_live_yyyyyyyyyyyyyyyyyyyy": "subscription_monthly",
    #
    "price_perpetual": "perpetual",
    "price_monthly": "subscription_monthly",
    "price_yearly": "subscription_yearly",
}
DEFAULT_EXPIRY = {
    "perpetual": PERPETUAL_EXPIRY,
    "subscription_monthly": None,
    "subscription_yearly": None,
}


def _require_admin():
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {ADMIN_API_KEY}"
    if not hmac.compare_digest(auth, expected):
        return jsonify({"error": "Unauthorized"}), 401
    return None


@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json(silent=True) or {}
    license_key = data.get("license_key", "")
    ip = request.remote_addr or ""

    crypto_ok = verify_license(license_key)
    db_result = (
        validate_key(license_key)
        if crypto_ok
        else {"valid": False, "reason": "crypto_fail"}
    )

    result = {
        "valid": crypto_ok and db_result.get("valid", False),
        "tier": db_result.get("tier", ""),
        "expires_at": db_result.get("expires_at"),
    }

    log_validation(license_key, ip, json.dumps(result))
    return jsonify(result)


@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature", "")

    if STRIPE_WEBHOOK_SECRET:
        try:
            import stripe

            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            return jsonify(
                {"error": f"Webhook signature verification failed: {e}"}
            ), 400
    else:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON"}), 400

    if event.get("type") == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        customer_email = session.get("customer_email") or session.get(
            "customer_details", {}
        ).get("email", "")
        customer_name = session.get("customer_details", {}).get("name", "")
        session_id = session.get("id", "")
        subscription_id = session.get("subscription", "")
        mode = session.get("mode", "payment")

        line_items = session.get("display_items", [])
        price_id = ""
        if not line_items:
            try:
                import stripe

                line_resp = stripe.checkout.Session.list_line_items(session_id, limit=1)
                items = line_resp.get("data", [])
                if items:
                    price_id = items[0].get("price", {}).get("id", "")
            except Exception:
                pass
        else:
            price_id = line_items[0].get("price", {}).get("id", "")

        tier = SUBSCRIPTION_TIERS.get(price_id, "perpetual")

        if mode == "subscription":
            tier = "subscription_monthly"
            if "year" in price_id.lower():
                tier = "subscription_yearly"

        if not customer_email:
            return jsonify({"error": "No customer email"}), 400

        user_id = f"{customer_email}::{session_id[:8]}"
        license_key = sign_license(user_id)
        if license_key is None:
            return jsonify({"error": "Key generation failed"}), 500

        expires_at = None
        if tier == "perpetual":
            expires_at = PERPETUAL_EXPIRY
        elif subscription_id:
            try:
                import stripe

                sub = stripe.Subscription.retrieve(subscription_id)
                expires_at = sub.get("current_period_end")
            except Exception:
                pass

        store_license(
            license_key=license_key,
            customer_email=customer_email,
            tier=tier,
            expires_at=expires_at,
            customer_name=customer_name,
            stripe_session_id=session_id,
            stripe_subscription_id=subscription_id,
        )

        send_license_email(customer_email, license_key, tier, customer_name)
        return jsonify({"status": "ok", "license_generated": True})

    if event.get("type") == "invoice.payment_failed":
        subscription_id = (
            event.get("data", {}).get("object", {}).get("subscription", "")
        )
        if subscription_id:
            with _get_conn() as conn:
                row = conn.execute(
                    "SELECT license_key FROM licenses WHERE stripe_subscription_id = ?",
                    (subscription_id,),
                ).fetchone()
                if row:
                    revoke_key(row["license_key"])

    return jsonify({"status": "received"})


@app.route("/admin/generate", methods=["POST"])
def admin_generate():
    err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    tier = data.get("tier", "perpetual")
    name = data.get("name", "")

    if not email:
        return jsonify({"error": "email required"}), 400
    if tier not in ("perpetual", "subscription_monthly", "subscription_yearly"):
        return jsonify({"error": "invalid tier"}), 400

    user_id = f"{email}::admin-{int(time.time())}"
    license_key = sign_license(user_id)
    if license_key is None:
        return jsonify({"error": "Key generation failed"}), 500

    expires_at = PERPETUAL_EXPIRY if tier == "perpetual" else None
    store_license(
        license_key=license_key,
        customer_email=email,
        tier=tier,
        expires_at=expires_at,
        customer_name=name,
    )

    send_license_email(email, license_key, tier, name)
    return jsonify({"status": "ok", "license_key": license_key})


@app.route("/admin/licenses", methods=["GET"])
def admin_list_licenses():
    err = _require_admin()
    if err:
        return err

    licenses = get_all_licenses()
    return jsonify({"licenses": licenses})


@app.route("/admin/revoke", methods=["POST"])
def admin_revoke():
    err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    license_key = data.get("license_key", "")
    if not license_key:
        return jsonify({"error": "license_key required"}), 400

    ok = revoke_key(license_key)
    return jsonify({"revoked": ok})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "license-server"})


if __name__ == "__main__":
    init_db()
    generate_key_pair()
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
