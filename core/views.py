from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Sum
from django.conf import settings
from .models import Transaction
from twilio.rest import Client

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
