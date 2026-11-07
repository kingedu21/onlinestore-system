import json
import logging
from decimal import Decimal

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from orders.models import Order
from .models import Payment

logger = logging.getLogger(__name__)

@csrf_exempt
def mpesa_callback(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return HttpResponseBadRequest('Invalid JSON payload')

    logger.info('M-Pesa callback received: %s', payload)

    callback = payload.get('Body', {}).get('stkCallback', {})
    checkout_request_id = callback.get('CheckoutRequestID')
    if not checkout_request_id:
        return HttpResponseBadRequest('Missing CheckoutRequestID')

    payment = Payment.objects.select_related('order').filter(checkout_request_id=checkout_request_id).first()
    if not payment:
        logger.warning('M-Pesa callback for unknown CheckoutRequestID: %s', checkout_request_id)
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Payment not found'}, status=404)

    result_code = callback.get('ResultCode')
    result_desc = callback.get('ResultDesc', '')
    metadata_items = callback.get('CallbackMetadata', {}).get('Item', [])
    metadata = {item.get('Name'): item.get('Value') for item in metadata_items}

    mpesa_receipt = metadata.get('MpesaReceiptNumber', '')
    amount = metadata.get('Amount')
    phone = metadata.get('PhoneNumber')

    payment.result_code = str(result_code) if result_code is not None else ''
    payment.result_desc = result_desc
    payment.mpesa_receipt_number = mpesa_receipt or ''
    if amount is not None:
        payment.amount = Decimal(str(amount))
    if phone:
        payment.phone_number = str(phone)
    payment.raw_callback = payload

    order = payment.order
    if str(result_code) == '0':
        payment.status = Payment.STATUS_SUCCESS
        order.payment_status = Order.PAYMENT_PAID
    else:
        payment.status = Payment.STATUS_FAILED
        order.payment_status = Order.PAYMENT_FAILED

    payment.save()
    order.save(update_fields=['payment_status'])

    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'OK'})
