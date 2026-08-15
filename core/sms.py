"""
Message Central SMS integration.

To activate real automatic SMS receipts:
1. Get your Customer ID and Auth Token from your Message Central dashboard.
2. Set these environment variables on your backend host (Render):
     MESSAGECENTRAL_CUSTOMER_ID
     MESSAGECENTRAL_AUTH_TOKEN
3. IMPORTANT: verify the exact endpoint/payload shape below against
   Message Central's current API docs before relying on it in production —
   this is a reasonable starting shape, not a confirmed-live integration.

Until those env vars are set, send_receipt_sms() does nothing and is
silently skipped — the app keeps working normally with WhatsApp-link
receipts only (see the frontend's "Send receipt" button).
"""
import os
import requests

CUSTOMER_ID = os.environ.get('MESSAGECENTRAL_CUSTOMER_ID')
AUTH_TOKEN = os.environ.get('MESSAGECENTRAL_AUTH_TOKEN')

SMS_API_URL = 'https://cpaas.messagecentral.com/verification/v3/send'


def send_receipt_sms(entry):
    if not CUSTOMER_ID or not AUTH_TOKEN:
        return

    message = (
        f"Thank you {entry.contributor_name}! We received Rs.{entry.amount} "
        f"towards this year's Vinayaka Chavithi chanda. - {entry.committee.name}"
    )

    requests.post(
        SMS_API_URL,
        params={
            'countryCode': '91',
            'customerId': CUSTOMER_ID,
            'flowType': 'SMS',
            'mobileNumber': entry.mobile,
        },
        headers={'authToken': AUTH_TOKEN},
        json={'message': message},
        timeout=8,
    )
