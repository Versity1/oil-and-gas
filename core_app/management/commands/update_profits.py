from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from core_app.models import UserPlan, Transaction


class Command(BaseCommand):
    help = 'Process daily profits for all active investment plans'

    def handle(self, *args, **options):
        now = timezone.now()
        yesterday = now - timedelta(hours=24)
        
        # Get active plans where the last profit was more than 24 hours ago
        active_plans = UserPlan.objects.filter(is_active=True, last_profit_at__lte=yesterday)
        
        count = 0
        for user_plan in active_plans:
            try:
                # Calculate daily profit
                daily_rate = Decimal(user_plan.plan.daily_profit_rate) / Decimal(100)
                profit_amount = user_plan.amount * daily_rate
                
                # Update User balance
                account = user_plan.user.account
                account.balance += profit_amount
                account.save()
                
                # Update UserPlan profit tracking
                user_plan.current_profit += profit_amount
                user_plan.last_profit_at = now
                
                # Create profit transaction
                Transaction.objects.create(
                    account=account,
                    transaction_type='profit',
                    amount=profit_amount,
                    description=f"Daily profit from {user_plan.plan.name}",
                    status='completed'
                )
                
                # Check if duration has ended
                elapsed_time = now - user_plan.start_date
                if elapsed_time.days >= user_plan.plan.duration_days:
                    user_plan.is_active = False
                    
                    # Return capital if applicable
                    if user_plan.plan.capital_return:
                        account.balance += user_plan.amount
                        account.save()
                        
                        # Create capital return transaction
                        Transaction.objects.create(
                            account=account,
                            transaction_type='capital_return',
                            amount=user_plan.amount,
                            description=f"Capital return from {user_plan.plan.name}",
                            status='completed'
                        )
                
                user_plan.save()
                count += 1
                self.stdout.write(f"Processed profit for {user_plan.user.username} - {user_plan.plan.name}")
                
            except Exception as e:
                self.stderr.write(f"Error processing plan for {user_plan.user.username}: {e}")
                continue
        
        self.stdout.write(self.style.SUCCESS(f"Successfully processed {count} user plans"))
