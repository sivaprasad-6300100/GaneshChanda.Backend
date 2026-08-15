"""
Message Central OTP verification for signup phone-number checks.

Separate from sms.py's plain receipt-message sender — this uses Message
Central's actual Verification API (send + validateOtp). Same env vars:
    MESSAGECENTRAL_CUSTOMER_ID
    MESSAGECENTRAL_AUTH_TOKEN

IMPORTANT: verify the exact endpoint/payload shape against Message Central's
current docs before relying on it in production.
"""
import os
import requests

CUSTOMER_ID = os.environ.get('MESSAGECENTRAL_CUSTOMER_ID')
AUTH_TOKEN = os.environ.get('MESSAGECENTRAL_AUTH_TOKEN')

SEND_OTP_URL = 'https://cpaas.messagecentral.com/verification/v3/send'
VALIDATE_OTP_URL = 'https://cpaas.messagecentral.com/verification/v3/validateOtp'


class OtpError(Exception):
    pass


def send_otp(phone):
    """Triggers an OTP SMS via Message Central. Returns the verificationId."""
    if not CUSTOMER_ID or not AUTH_TOKEN:
        raise OtpError('SMS OTP is not configured on the server.')

    resp = requests.post(
        SEND_OTP_URL,
        params={
            'countryCode': '91',
            'customerId': CUSTOMER_ID,
            'flowType': 'SMS',
            'mobileNumber': phone,
            'otpLength': 6,
        },
        headers={'authToken': AUTH_TOKEN},
        timeout=8,
    )
    resp.raise_for_status()
    data = resp.json()
    verification_id = data.get('data', {}).get('verificationId')
    if not verification_id:
        raise OtpError('Could not start OTP verification. Try again.')
    return verification_id


def validate_otp(phone, verification_id, code):
    """Validates the code the user typed. Returns True/False."""
    if not CUSTOMER_ID or not AUTH_TOKEN:
        raise OtpError('SMS OTP is not configured on the server.')

    resp = requests.get(
        VALIDATE_OTP_URL,
        params={
            'countryCode': '91',
            'mobileNumber': phone,
            'verificationId': verification_id,
            'customerId': CUSTOMER_ID,
            'code': code,
        },
        headers={'authToken': AUTH_TOKEN},
        timeout=8,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get('data', {}).get('verificationStatus') == 'VERIFICATION_COMPLETED'