# core/kafka_consumer.py
from kafka import KafkaConsumer
import json
from .models import Transaction
import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analytics_dashboard.settings")
django.setup()

consumer = KafkaConsumer(
    'transactions',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='latest',
    group_id='transaction-group'
)

for msg in consumer:
    data = json.loads(msg.value)
    Transaction.objects.create(
        amount=data['amount'],
        merchant=data['merchant'],
        user_id=data['user_id'],
        description=data['description']
    )
