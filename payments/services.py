import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from django.conf import settings


class MpesaError(Exception):
    pass


@dataclass(frozen=True)
class MpesaConfig:
    consumer_key: str
    consumer_secret: str
    shortcode: str
    passkey: str
    callback_url: str
    transaction_type: str


def _get_config() -> MpesaConfig:
    return MpesaConfig(
        consumer_key=getattr(settings, 'MPESA_CONSUMER_KEY', ''),
        consumer_secret=getattr(settings, 'MPESA_CONSUMER_SECRET', ''),
        shortcode=getattr(settings, 'MPESA_SHORTCODE', ''),
        passkey=getattr(settings, 'MPESA_PASSKEY', ''),
        callback_url=getattr(settings, 'MPESA_CALLBACK_URL', ''),
        transaction_type=getattr(settings, 'MPESA_STK_TRANSACTION_TYPE', 'CustomerPayBillOnline'),
    )


def is_mpesa_configured() -> bool:
    config = _get_config()
    return all(
        [
            config.consumer_key,
            config.consumer_secret,
            config.shortcode,
            config.passkey,
            config.callback_url,
        ]
    )


def normalize_phone_number(phone: str) -> str:
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('0') and len(digits) == 10:
        digits = f'254{digits[1:]}'
    elif digits.startswith('7') and len(digits) == 9:
        digits = f'254{digits}'
    elif digits.startswith('254') and len(digits) == 12:
        digits = digits
    else:
        return ''
    return digits


def _mpesa_base_url() -> str:
    env = getattr(settings, 'MPESA_ENV', 'sandbox').lower()
    if env == 'live':
        return 'https://api.safaricom.co.ke'
    return 'https://sandbox.safaricom.co.ke'


def _request_json(url: str, method: str = 'GET', data: dict | None = None, headers: dict | None = None) -> dict:
    payload = None
    request_headers = headers.copy() if headers else {}
    if data is not None:
        payload = json.dumps(data).encode('utf-8')
        request_headers.setdefault('Content-Type', 'application/json')
    req = Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            body = response.read().decode('utf-8')
        return json.loads(body) if body else {}
    except HTTPError as exc:
        details = exc.read().decode('utf-8')
        raise MpesaError(f'M-Pesa request failed ({exc.code}): {details}') from exc
    except URLError as exc:
        raise MpesaError(f'M-Pesa request failed: {exc.reason}') from exc


def _access_token(config: MpesaConfig) -> str:
    auth = f'{config.consumer_key}:{config.consumer_secret}'.encode('utf-8')
    encoded = base64.b64encode(auth).decode('utf-8')
    url = f'{_mpesa_base_url()}/oauth/v1/generate?grant_type=client_credentials'
    data = _request_json(url, headers={'Authorization': f'Basic {encoded}'})
    token = data.get('access_token', '')
    if not token:
        raise MpesaError('Failed to obtain M-Pesa access token.')
    return token


def _stk_password(config: MpesaConfig, timestamp: str) -> str:
    raw = f'{config.shortcode}{config.passkey}{timestamp}'.encode('utf-8')
    return base64.b64encode(raw).decode('utf-8')


def _mpesa_timestamp() -> str:
    kenya_time = datetime.now(tz=ZoneInfo('Africa/Nairobi'))
    return kenya_time.strftime('%Y%m%d%H%M%S')


def stk_push(phone: str, amount: Decimal, account_reference: str, transaction_desc: str) -> dict:
    if not is_mpesa_configured():
        raise MpesaError('M-Pesa is not configured. Set MPESA_* settings before initiating STK push.')

    config = _get_config()
    timestamp = _mpesa_timestamp()
    token = _access_token(config)
    amount_value = int(amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    payload = {
        'BusinessShortCode': config.shortcode,
        'Password': _stk_password(config, timestamp),
        'Timestamp': timestamp,
        'TransactionType': config.transaction_type,
        'Amount': amount_value,
        'PartyA': phone,
        'PartyB': config.shortcode,
        'PhoneNumber': phone,
        'CallBackURL': config.callback_url,
        'AccountReference': account_reference,
        'TransactionDesc': transaction_desc,
    }
    url = f'{_mpesa_base_url()}/mpesa/stkpush/v1/processrequest'
    return _request_json(url, method='POST', data=payload, headers={'Authorization': f'Bearer {token}'})
