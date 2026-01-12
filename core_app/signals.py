from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal
import uuid
from .models import Account, Deposit, Withdrawal, Transaction, Notification
from .utils import send_transaction_email

@receiver(post_save, sender=User)
def create_user_account(sender, instance, created, **kwargs):
    if created:
        # Generate unique referral code
        referral_code = str(uuid.uuid4().hex)[:8].upper()
        # Ensure uniqueness
        while Account.objects.filter(referral_code=referral_code).exists():
            referral_code = str(uuid.uuid4().hex)[:8].upper()
        
        Account.objects.create(user=instance, referral_code=referral_code)

@receiver(post_save, sender=User)
def save_user_account(sender, instance, **kwargs):
    if hasattr(instance, 'account'):
        instance.account.save()

@receiver(pre_save, sender=Deposit)
def track_deposit_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Deposit.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Deposit.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(pre_save, sender=Withdrawal)
def track_withdrawal_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Withdrawal.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Withdrawal.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Deposit)
def handle_deposit_update(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)
    
    if instance.status == 'completed':
        # Check if we already processed this deposit (prevent multiple balance updates)
        txn_ref = f"DEP-{instance.id}"
        if not Transaction.objects.filter(reference=txn_ref).exists():
            with transaction.atomic():
                account = instance.user.account
                # If it's a direct investment deposit, we might not want to add to balance 
                # OR we add to balance and then immediately deduct.
                # Adding to balance first is cleaner for ledger history.
                account.balance = Decimal(str(account.balance)) + instance.amount
                account.save()
                
                txn = Transaction.objects.create(
                    account=account,
                    transaction_type='deposit',
                    amount=instance.amount,
                    description=f"Crypto Deposit: {instance.payment_method.name}",
                    status='completed',
                    reference=txn_ref
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
        
        # Notification Logic (Decoupled from Transaction to allow retries/fixes)
        if old_status != 'completed':
            Notification.objects.create(
                user=instance.user,
                title="Deposit Confirmed",
                message=f"Your deposit of ${instance.amount:,.2f} has been successfully confirmed.",
                notification_type="success"
            )
            
            # Referral Bonus Logic
            account = instance.user.account
            if account.referred_by:
                referrer_account = account.referred_by
                bonus_amount = instance.amount * Decimal('0.10')  # 10% bonus
                
                # Credit referrer's balance
                referrer_account.balance = Decimal(str(referrer_account.balance)) + bonus_amount
                referrer_account.referral_earnings = Decimal(str(referrer_account.referral_earnings)) + bonus_amount
                referrer_account.save()
                
                # Create transaction record for referrer
                Transaction.objects.create(
                    account=referrer_account,
                    transaction_type='deposit',
                    amount=bonus_amount,
                    description=f"Referral bonus from {instance.user.username}'s deposit",
                    status='completed',
                    reference=f"REF-{instance.id}-{account.user.id}"
                )
                
                # Notify referrer
                Notification.objects.create(
                    user=referrer_account.user,
                    title="Referral Bonus!",
                    message=f"You earned ${bonus_amount:,.2f} referral bonus from {instance.user.username}'s deposit.",
                    notification_type="profit"
                )

    elif instance.status == 'failed' and old_status != 'failed':
        Notification.objects.create(
            user=instance.user,
            title="Deposit Failed",
            message=f"Your deposit of ${instance.amount:,.2f} was unsuccessful or rejected.",
            notification_type="warning"
        )

@receiver(post_save, sender=Withdrawal)
def handle_withdrawal_update(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)

    if instance.status == 'completed':
        # Check if we already processed this withdrawal
        txn_ref = f"WTH-{instance.id}"
        if not Transaction.objects.filter(reference=txn_ref).exists():
            with transaction.atomic():
                account = instance.user.account
                # Note: Balance check should have happened during request or here
                account.balance = Decimal(str(account.balance)) - instance.amount
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
                
                send_transaction_email(instance.user, txn)
        
        # Notification Logic
        if old_status != 'completed':
            Notification.objects.create(
                user=instance.user,
                title="Withdrawal Approved",
                message=f"Your withdrawal of ${instance.amount:,.2f} has been processed.",
                notification_type="success"
            )

    elif instance.status == 'failed' and old_status != 'failed':
        Notification.objects.create(
            user=instance.user,
            title="Withdrawal Rejected",
            message=f"Your withdrawal request for ${instance.amount:,.2f} was declined.",
            notification_type="warning"
        )
