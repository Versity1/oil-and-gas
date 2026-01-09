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
