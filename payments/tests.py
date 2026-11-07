import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from orders.models import Order, Receipt
from .models import Payment


class PaymentReceiptGenerationTests(TestCase):
    def test_receipt_is_auto_created_when_payment_is_confirmed(self):
        user = User.objects.create_user(username='buyer1', password='secret123')
        order = Order.objects.create(
            user=user,
            total_price='1500.00',
            payment_method=Order.METHOD_MPESA,
            payment_status=Order.PAYMENT_PENDING,
        )
        payment = Payment.objects.create(
            order=order,
            payment_method=Payment.METHOD_MPESA,
            status=Payment.STATUS_PENDING,
            amount='1500.00',
        )

        payment.status = Payment.STATUS_SUCCESS
        payment.save(update_fields=['status'])
        order.refresh_from_db()

        self.assertEqual(order.payment_status, Order.PAYMENT_PAID)
        self.assertTrue(Receipt.objects.filter(order=order).exists())

    def test_mpesa_callback_marks_order_paid_and_generates_receipt(self):
        user = User.objects.create_user(username='buyer2', password='secret123')
        order = Order.objects.create(
            user=user,
            total_price='2200.00',
            payment_method=Order.METHOD_MPESA,
            payment_status=Order.PAYMENT_PENDING,
        )
        payment = Payment.objects.create(
            order=order,
            payment_method=Payment.METHOD_MPESA,
            status=Payment.STATUS_PENDING,
            amount='2200.00',
            checkout_request_id='ws_CO_123456789',
        )

        payload = {
            'Body': {
                'stkCallback': {
                    'CheckoutRequestID': 'ws_CO_123456789',
                    'ResultCode': 0,
                    'ResultDesc': 'The service request is processed successfully.',
                    'CallbackMetadata': {
                        'Item': [
                            {'Name': 'Amount', 'Value': 2200},
                            {'Name': 'MpesaReceiptNumber', 'Value': 'TST123ABC'},
                            {'Name': 'PhoneNumber', 'Value': 254712345678},
                        ]
                    },
                }
            }
        }

        response = self.client.post(
            reverse('mpesa_callback'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(payment.status, Payment.STATUS_SUCCESS)
        self.assertEqual(payment.mpesa_receipt_number, 'TST123ABC')
        self.assertEqual(order.payment_status, Order.PAYMENT_PAID)
        self.assertTrue(Receipt.objects.filter(order=order).exists())
