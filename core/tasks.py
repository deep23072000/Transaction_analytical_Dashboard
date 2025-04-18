from celery import shared_task
from .models import Transaction
from .notifications import send_sms_alert

@shared_task
def detect_fraud():
    transactions = Transaction.objects.filter(is_fraud=False)

    for tx in transactions:
        if tx.amount > 1000 or "suspicious" in tx.description.lower():
            tx.is_fraud = True
            tx.save()

            # 🚨 Send SMS alert
            msg = (
                f"🚨 Fraud Alert!\n"
                f"TX ID: {tx.id}\n"
                f"Amount: ${tx.amount}\n"
                f"Merchant: {tx.merchant}\n"
                f"User: {tx.user_id}"
            )
            send_sms_alert(msg)
