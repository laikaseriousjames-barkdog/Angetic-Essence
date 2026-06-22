# Stripe Payment Setup Guide

## Products to create in Stripe Dashboard

### Perpetual License ($499 / $999)

| Tier | Price | Stripe Price ID |
|------|-------|-----------------|
| Starter | $499 one-time | `price_perpetual_starter` |
| Professional | $999 one-time | `price_perpetual_pro` |

1. Go to Stripe Dashboard > Products > Add Product
2. Name: "Angetic Essence — Perpetual License"
3. Description: "One-time purchase, lifetime access"
4. Pricing: Standard pricing, $499.00 / one-time
5. Save, copy the `price_xxx` ID
6. Repeat for Professional tier at $999

### Monthly Subscription ($29 / $79)

1. Name: "Angetic Essence — Monthly"
2. Pricing: Recurring, $29.00 / month
3. Save, copy the `price_xxx` ID → set as `price_monthly`
4. Repeat for $79/month tier → set as `price_monthly_pro`

### Yearly Subscription ($29 / $79 per year, billed annually)

1. Name: "Angetic Essence — Yearly"
2. Pricing: Recurring, $29.00 / year
3. Save, copy the `price_xxx` ID → set as `price_yearly`
4. Repeat for $79/year → set as `price_yearly_pro`

## Update configuration

### `license_server/app.py`

Replace the placeholder `SUBSCRIPTION_TIERS` keys with the real Stripe price IDs:

```python
SUBSCRIPTION_TIERS = {
    "price_live_xxxxxxxxxxxxx": "perpetual",
    "price_live_yyyyyyyyyyyyy": "subscription_monthly",
    "price_live_zzzzzzzzzzzzz": "subscription_yearly",
}
```

### Webhook setup

1. Stripe Dashboard > Developers > Webhooks > Add endpoint
2. URL: `https://your-server.com/stripe-webhook`
3. Events: `checkout.session.completed`, `invoice.payment_failed`
4. Copy the signing secret → set as `STRIPE_WEBHOOK_SECRET` in `.env`

### Environment variables

```ini
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret_here
```

## Testing

```bash
# Test mode keys start with sk_test_ / whsec_test_
# Use Stripe CLI to forward webhooks locally:
stripe listen --forward-to localhost:8080/stripe-webhook
stripe trigger checkout.session.completed
```
