from django.shortcuts import render, redirect
from django.db.models import Sum
from django.conf import settings
from .models import Transaction, FailedPayment
from twilio.rest import Client
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from datetime import datetime

# ------------------ Stripe Setup ------------------
stripe.api_key = settings.STRIPE_SECRET_KEY

# ------------------ Success Page ------------------
def success(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return render(request, 'error.html', {'error': 'Session ID missing'})

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        customer_id = session.customer

        if customer_id:
            customer = stripe.Customer.retrieve(customer_id)
            return render(request, 'success.html', {'customer': customer, 'session': session})
        else:
            return render(request, 'error.html', {'error': 'Customer ID missing in session data'})
    except stripe.error.StripeError as e:
        return render(request, 'error.html', {'error': str(e)})

# ------------------ Checkout ------------------
def checkout(request):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'unit_amount': 5000,
                'product_data': {
                    'name': 'Transaction Charge',
                },
            },
            'quantity': 1,
        }],
        mode='payment',
        customer_creation='always',
        success_url='http://127.0.0.1:8000/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='http://127.0.0.1:8000/cancel',
    )
    return render(request, 'checkout.html', {
        'session_id': session.id,
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY
    })

# ------------------ Stripe Webhook ------------------
@csrf_exempt
def stripe_webhook(request):
    print("✅ Stripe Webhook Triggered")
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        print("❌ Webhook error:", str(e))
        return HttpResponse(status=400)

    # ✅ Successful payment
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print("🎯 Checkout Session ID:", session.get('id'))

        if session.get('payment_status') == 'paid':
            customer_id = session.get('customer')
            amount_total = session.get('amount_total') or 0
            description = 'Stripe Checkout Payment'
            timestamp = datetime.fromtimestamp(session.get('created'))

            try:
                customer = stripe.Customer.retrieve(customer_id)
                email = customer.get('email', '')
                name = customer.get('name', '')

                transaction = Transaction.objects.create(
                    amount=amount_total / 100,
                    transaction_type='credit',
                    description=f"{description} (Customer: {name or email})",
                    timestamp=timestamp
                )

                # Send SMS notification on successful payment
                send_success_sms(name or email, amount_total / 100)

                print("✅ Transaction saved and SMS sent!")

            except Exception as e:
                print("❌ Failed to save transaction:", str(e))
                return HttpResponse(status=500)

    # ❌ Failed payment
    elif event['type'] == 'payment_intent.payment_failed':
        intent = event['data']['object']
        error_message = intent.get('last_payment_error', {}).get('message', 'Unknown error')
        amount = intent.get('amount', 0)
        customer_id = intent.get('customer')
        email = None

        if customer_id:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                email = customer.get('email')
            except Exception as e:
                print("⚠️ Could not retrieve customer:", str(e))

        # Save to DB
        FailedPayment.objects.create(
            amount=amount / 100,
            error_message=error_message,
            customer_id=customer_id,
            email=email
        )

        # Send SMS Alert for failed payment
        send_failed_payment_sms(amount, error_message, email)

        print("❌ Payment failed logged and alert sent.")

    return HttpResponse(status=200)

# ------------------ Dashboard ------------------
def dashboard(request):
    transactions = Transaction.objects.all()
    total_transactions = transactions.count()
    total_revenue = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    fraud_count = transactions.filter(is_fraud=True).count()

    context = {
        'transactions': transactions,
        'total_transactions': total_transactions,
        'total_revenue': total_revenue,
        'fraud_count': fraud_count,
    }
    return render(request, 'dashboard.html', context)

# ------------------ Transaction API ------------------
def transaction_api(request):
    transactions = Transaction.objects.all().values(
        'id', 'amount', 'description', 'timestamp', 'transaction_type', 'is_fraud'
    )
    data = list(transactions)
    return JsonResponse(data, safe=False)

# ------------------ Transaction List Page ------------------
def transaction_list(request):
    transactions = Transaction.objects.all()
    return render(request, 'core/transactions.html', {'transactions': transactions})

# ------------------ Fraud Alerts Page ------------------
def fraud_alerts(request):
    fraudulent = Transaction.objects.filter(is_fraud=True)
    return render(request, 'core/fraud_alerts.html', {'fraudulent': fraudulent})

# ------------------ Fraud Detection Logic ------------------
def detect_fraud(transaction):
    if float(transaction.amount) > 1000:
        return True
    if 'suspicious' in transaction.description.lower():
        return True
    return False

# ------------------ Send SMS via Twilio ------------------
def send_success_sms(customer_name, amount):
    """
    Send SMS on successful transaction using Twilio.
    """
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    message = client.messages.create(
        body=f"""
✅ Payment Successful!
Customer: {customer_name}
Amount: ${amount}
Thank you for your payment!
        """.strip(),
        from_=settings.TWILIO_PHONE_NUMBER,
        to=settings.ALERT_RECEIVER_PHONE
    )
    print("✅ Success SMS Sent!")

def send_failed_payment_sms(amount, error_message, customer_email=None):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message_body = f"""
❌ Payment Failed!
Amount: ${amount / 100:.2f}
Error: {error_message}
{f'Email: {customer_email}' if customer_email else ''}
    """.strip()

    message = client.messages.create(
        body=message_body,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=settings.ALERT_RECEIVER_PHONE
    )
    print("❌ Failed payment SMS sent.")

from .models import FailedPayment

def failed_payments(request):
    failed = FailedPayment.objects.all().order_by('-timestamp')
    return render(request, 'failed_payments.html', {'failed_payments': failed})



# ==========pdf


from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from .models import Transaction, FailedPayment


def download_combined_payments_pdf(request):
    # Create a HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="payments_summary.pdf"'

    # Set up canvas
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, "Payment Summary Report")
    y -= 40

    # Success Payments Section
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "✅ Successful Transactions")
    y -= 20

    p.setFont("Helvetica", 10)
    transactions = Transaction.objects.all()
    for txn in transactions:
        text = f"ID: {txn.id} | Amount: ${txn.amount:.2f} | Type: {txn.transaction_type} | Desc: {txn.description} | Time: {txn.timestamp.strftime('%Y-%m-%d %H:%M')}"
        p.drawString(50, y, text)
        y -= 15
        if y < 100:
            p.showPage()
            y = height - 50

    # Space
    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "❌ Failed Transactions")
    y -= 20

    # Failed Payments Section
    p.setFont("Helvetica", 10)
    failed = FailedPayment.objects.all()
    for fp in failed:
        text = f"Amount: ${fp.amount:.2f} | Error: {fp.error_message} | Email: {fp.email or 'N/A'} | Time: {fp.timestamp.strftime('%Y-%m-%d %H:%M')}"
        p.drawString(50, y, text)
        y -= 15
        if y < 100:
            p.showPage()
            y = height - 50

    # Finalize PDF
    p.showPage()
    p.save()
    return response
