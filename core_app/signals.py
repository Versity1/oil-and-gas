from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction
from .models import Account, Deposit, Withdrawal, Transaction

@receiver(post_save, sender=User)
def create_user_account(sender, instance, created, **kwargs):
    if created:
        Account.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_account(sender, instance, **kwargs):
    if hasattr(instance, 'account'):
        instance.account.save()

@receiver(post_save, sender=Deposit)
def handle_deposit_update(sender, instance, created, **kwargs):
    if instance.status == 'completed':
        # Check if we already processed this deposit (prevent multiple balance updates)
        txn_ref = f"DEP-{instance.id}"
        if not Transaction.objects.filter(reference=txn_ref).exists():
            with transaction.atomic():
                account = instance.user.account
                account.balance += instance.amount
                account.save()
                
                Transaction.objects.create(
                    account=account,
                    transaction_type='deposit',
                    amount=instance.amount,
                    description=f"Crypto Deposit: {instance.payment_method.name}",
                    status='completed',
                    reference=txn_ref
                )

@receiver(post_save, sender=Withdrawal)
def handle_withdrawal_update(sender, instance, created, **kwargs):
    if instance.status == 'completed':
        # Check if we already processed this withdrawal
        txn_ref = f"WTH-{instance.id}"
        if not Transaction.objects.filter(reference=txn_ref).exists():
            with transaction.atomic():
                account = instance.user.account
                # Note: Balance check should have happened during request or here
                account.balance -= instance.amount
                account.save()
                
                Transaction.objects.create(
                    account=account,
                    transaction_type='withdrawal',
                    amount=instance.amount,
                    description=f"Crypto Withdrawal: {instance.network}",
                    status='completed',
                    reference=txn_ref
                )
