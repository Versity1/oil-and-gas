from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction
from .models import Account, Deposit, Withdrawal, Transaction, Notification
from .utils import send_transaction_email

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
                # If it's a direct investment deposit, we might not want to add to balance 
                # OR we add to balance and then immediately deduct.
                # Adding to balance first is cleaner for ledger history.
                account.balance += instance.amount
                account.save()
                
                txn = Transaction.objects.create(
                    account=account,
                    transaction_type='deposit',
                    amount=instance.amount,
                    description=f"Crypto Deposit: {instance.payment_method.name}",
                    status='completed',
                    reference=txn_ref
                )
                
                # Notification for success
                Notification.objects.create(
                    user=instance.user,
                    title="Deposit Confirmed",
                    message=f"Your deposit of ${instance.amount:,.2f} has been successfully confirmed.",
                    notification_type="success"
                )
                
                send_transaction_email(instance.user, txn)

                # Automated Investment Logic
                if instance.linked_project or instance.linked_asset or instance.linked_plan:
                    invest_amount = instance.invest_amount or instance.amount
                    if account.balance >= invest_amount:
                        from .models import Investment, UserPlan
                        import time
                        
                        if instance.linked_project:
                            Investment.objects.create(
                                user=instance.user,
                                project=instance.linked_project,
                                amount_invested=invest_amount,
                                purchase_price=invest_amount,
                                status='active'
                            )
                            description = f"Investment in Project: {instance.linked_project.title}"
                            ref_prefix = f"INV-PRJ-{instance.linked_project.id}"
                        elif instance.linked_asset:
                            units = invest_amount / instance.linked_asset.current_price
                            Investment.objects.create(
                                user=instance.user,
                                asset=instance.linked_asset,
                                amount_invested=invest_amount,
                                units=units,
                                purchase_price=instance.linked_asset.current_price,
                                status='active'
                            )
                            description = f"Investment in Asset: {instance.linked_asset.name}"
                            ref_prefix = f"INV-AST-{instance.linked_asset.id}"
                        elif instance.linked_plan:
                            UserPlan.objects.create(
                                user=instance.user,
                                plan=instance.linked_plan,
                                amount=invest_amount,
                                is_active=True
                            )
                            description = f"Investment in Plan: {instance.linked_plan.name}"
                            ref_prefix = f"INV-PLN-{instance.linked_plan.id}"

                        account.balance -= invest_amount
                        account.save()

                        Transaction.objects.create(
                            account=account,
                            transaction_type='withdrawal',
                            amount=invest_amount,
                            description=description,
                            status='completed',
                            reference=f"{ref_prefix}-{instance.user.id}-{int(time.time())}"
                        )

    elif instance.status == 'failed':
        # Simple check to avoid duplicate failure notifications if saved multiple times?
        # For now, we assume status change to failed is a one-time event or infrequent enough.
        # Ideally we'd check if a recent notification exists, but let's keep it simple.
        Notification.objects.create(
            user=instance.user,
            title="Deposit Failed",
            message=f"Your deposit of ${instance.amount:,.2f} was unsuccessful or rejected.",
            notification_type="warning"
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
                
                wallet_info = f" ({instance.wallet_name})" if instance.wallet_name else ""
                txn = Transaction.objects.create(
                    account=account,
                    transaction_type='withdrawal',
                    amount=instance.amount,
                    description=f"Crypto Withdrawal{wallet_info}: {instance.network}",
                    status='completed',
                    reference=txn_ref
                )
                
                # Notification for success
                Notification.objects.create(
                    user=instance.user,
                    title="Withdrawal Approved",
                    message=f"Your withdrawal of ${instance.amount:,.2f} has been processed.",
                    notification_type="success"
                )
                
                send_transaction_email(instance.user, txn)

    elif instance.status == 'failed':
        Notification.objects.create(
            user=instance.user,
            title="Withdrawal Rejected",
            message=f"Your withdrawal request for ${instance.amount:,.2f} was declined.",
            notification_type="warning"
        )
