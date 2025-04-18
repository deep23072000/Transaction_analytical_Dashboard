from twilio.rest import Client
from django.conf import settings

def send_sms_alert(body):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    try:
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=settings.ALERT_RECEIVER_PHONE
        )
        print(f"✅ SMS sent: SID {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")
