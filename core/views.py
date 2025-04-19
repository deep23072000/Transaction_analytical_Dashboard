from django.shortcuts import render, redirect
from django.db.models import Sum
from django.conf import settings
from .models import Transaction
from twilio.rest import Client
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse


#------------------------------success
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



#--------stripe -------------------------

stripe.api_key = settings.STRIPE_SECRET_KEY

def checkout(request):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'unit_amount': 5000,  # $50
                'product_data': {
                    'name': 'Transaction Charge',
                },
            },
            'quantity': 1,
        }],
        mode='payment',
        customer_creation='always',  # 🔥 This line ensures a customer is created
        success_url='http://127.0.0.1:8000/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='http://127.0.0.1:8000/cancel',
    )
    return render(request, 'checkout.html', {
        'session_id': session.id,
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY
    })

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # ✅ Update your transaction model here
        # mark transaction as paid, log time, etc.

    return HttpResponse(status=200)

# --- Dashboard View ---
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

# --- Transaction API (for Chart.js) ---
def transaction_api(request):
    transactions = Transaction.objects.all().values(
        'id', 'amount', 'description', 'timestamp', 'transaction_type', 'is_fraud'
    )
    data = list(transactions)
    return JsonResponse(data, safe=False)

# --- Transaction List Page ---
def transaction_list(request):
    transactions = Transaction.objects.all()
    return render(request, 'core/transactions.html', {'transactions': transactions})

# --- Fraud Alerts Page ---
def fraud_alerts(request):
    fraudulent = Transaction.objects.filter(is_fraud=True)
    return render(request, 'core/fraud_alerts.html', {'fraudulent': fraudulent})

# --- Fraud Detection Logic ---
def detect_fraud(transaction):
    # You can add more complex rules or ML model later
    if float(transaction.amount) > 1000:
        return True
    if 'suspicious' in transaction.description.lower():
        return True
    return False

# --- Send SMS Using Twilio ---
def send_fraud_sms(transaction):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    print("FROM:", settings.TWILIO_PHONE_NUMBER)  # Debug print
    print("TO:", settings.ALERT_RECEIVER_PHONE)   # Debug print

    message = client.messages.create(
        body=f"""
🚨 Fraud Detected!
Type: {transaction.transaction_type}
Amount: ${transaction.amount}
Description: {transaction.description}
Time: {transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        """.strip(),
        from_=settings.TWILIO_PHONE_NUMBER,
        to=settings.ALERT_RECEIVER_PHONE
    )
        
# --- Create Transaction View ---
def create_transaction(request):
    if request.method == 'POST':
        try:
            amount = float(request.POST['amount'])
            transaction_type = request.POST['transaction_type']
            description = request.POST['description']
        except KeyError as e:
            return JsonResponse({"error": f"Missing field: {str(e)}"}, status=400)

        # Create the transaction
        transaction = Transaction.objects.create(
            amount=amount,
            transaction_type=transaction_type,
            description=description
        )

        # Fraud detection
        if detect_fraud(transaction):
            transaction.is_fraud = True
            transaction.save()
            send_fraud_sms(transaction)

        return redirect('dashboard')

    transactions = Transaction.objects.all()
    return render(request, 'create_transaction.html', {'transactions': transactions})
