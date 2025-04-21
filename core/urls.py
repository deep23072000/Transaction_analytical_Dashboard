# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Main dashboard
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('fraud-alerts/', views.fraud_alerts, name='fraud_alerts'),
    path('api/transactions/', views.transaction_api, name='transaction_api'),  # For AJAX/Chart
    # path('new-transaction/', views.create_transaction, name='create_transaction'),
    path('checkout/', views.checkout, name='checkout'),  # ADD this line for checkout
    path('success/', views.success, name='success'),
    path('stripe_webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('failed-payments/', views.failed_payments, name='failed_payments'),
    path('download/pdf/', views.download_combined_payments_pdf, name='download_pdf'),


]
