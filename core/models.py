# core/models.py

from django.db import models

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_fraud = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - ${self.amount}"




class FailedPayment(models.Model):
    amount = models.FloatField()
    error_message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    customer_id = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"Failed Payment - ${self.amount} - {self.timestamp}"


