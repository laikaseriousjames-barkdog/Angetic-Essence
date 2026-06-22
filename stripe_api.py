"""Phase 4: Stripe Payment Integration.

Placeholder functions for stripe payment processing.
Set STRIPE_SECRET_KEY env var to activate.
"""

import os
import json
from core.logger import setup_logger

try:
    import stripe as stripe_lib
except ImportError:
    stripe_lib = None


class StripeIntegration:
    def __init__(self, config: dict):
        self.logger = setup_logger("stripe")
        self.secret_key = os.environ.get(
            "STRIPE_SECRET_KEY",
            config.get("monetization", {}).get("stripe_secret_key", ""),
        )
        self.enabled = bool(self.secret_key and stripe_lib)
        if self.enabled:
            stripe_lib.api_key = self.secret_key
            self.logger.info("Stripe integration enabled.")
        else:
            self.logger.warning("Stripe not configured (set STRIPE_SECRET_KEY).")

    def create_product(
        self, name: str, description: str = "", price_cents: int = 999
    ) -> dict | None:
        if not self.enabled:
            return {"error": "Stripe not enabled"}
        try:
            product = stripe_lib.Product.create(name=name, description=description)
            price = stripe_lib.Price.create(
                product=product.id,
                unit_amount=price_cents,
                currency="usd",
            )
            self.logger.info(f"Created product {product.id} with price {price.id}")
            return {"product_id": product.id, "price_id": price.id}
        except Exception as e:
            self.logger.error(f"Stripe product creation failed: {e}")
            return {"error": str(e)}

    def create_checkout_session(
        self,
        price_id: str,
        success_url: str = "https://example.com/success",
        cancel_url: str = "https://example.com/cancel",
        customer_email: str = "",
    ) -> dict | None:
        if not self.enabled:
            return {"error": "Stripe not enabled"}
        try:
            session = stripe_lib.checkout.Session.create(
                line_items=[{"price": price_id, "quantity": 1}],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email or None,
            )
            self.logger.info(f"Created checkout session {session.id}")
            return {"session_id": session.id, "url": session.url}
        except Exception as e:
            self.logger.error(f"Stripe session creation failed: {e}")
            return {"error": str(e)}

    def list_products(self) -> list:
        if not self.enabled:
            return []
        try:
            products = stripe_lib.Product.list(limit=10)
            return [{"id": p.id, "name": p.name, "active": p.active} for p in products]
        except Exception as e:
            self.logger.error(f"Stripe list failed: {e}")
            return []
