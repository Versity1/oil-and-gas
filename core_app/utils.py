from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

def send_transaction_email(user, transaction):
    subject = f"Transaction Notification: {transaction.transaction_type.capitalize()}"
    
    context = {
        'user': user,
        'transaction': transaction,
        'balance': user.account.balance
    }
    
    # We could use templates for cleaner emails if they exist.
    # For now, let's just use a simple string logic.
    
    message = f"""
    Dear {user.first_name or user.username},

    A {transaction.transaction_type} of {transaction.amount} has been successfully processed on your account.

    Transaction Details:
    - Type: {transaction.transaction_type.capitalize()}
    - Amount: {transaction.amount}
    - Status: {transaction.status.capitalize()}
    - Reference: {transaction.reference}
    - Date: {transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

    Your current account balance is: {user.account.balance}

    Thank you for choosing Techodrill Oil and Gas.

    Best regards,
    The Techodrill Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@techodrill.com',
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending email: {e}")

def send_transaction_request_email(user, request_type, amount, withdrawal=None):
    subject = f"Transaction Request Received: {request_type.capitalize()}"
    
    wallet_details = ""
    if request_type == 'withdrawal' and withdrawal:
        wallet_name = f"\n    - Wallet Name: {withdrawal.wallet_name}" if withdrawal.wallet_name else ""
        wallet_details = f"""
    Withdrawal Details:{wallet_name}
    - Wallet Address: {withdrawal.wallet_address}
    - Network: {withdrawal.network}"""

    message = f"""
    Dear {user.first_name or user.username},

    We have received your {request_type} request for {amount}.{wallet_details}

    Our team is currently verifying the transaction. You will receive another notification once it has been processed and credited/debited from your balance.

    Thank you for choosing Techodrill Oil and Gas.

    Best regards,
    The Techodrill Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@techodrill.com',
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending request email: {e}")
