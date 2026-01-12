"""
Management command to process daily investment profits.
Run this via cron job daily: python manage.py process_daily_profits

This command:
1. Finds all active UserPlans
2. Calculates daily profit based on the plan's daily_profit_rate
3. Adds profit to user's account balance
4. Creates a transaction record
5. If plan has matured (duration_days reached), returns capital if applicable
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import timedelta
import logging

from core_app.models import UserPlan, Account, Transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process daily investment profits for all active plans'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(f'Processing daily profits at {now}')
        
        # Get all active user plans
        active_plans = UserPlan.objects.filter(is_active=True).select_related('user', 'plan', 'user__account')
        
        profits_processed = 0
        matured_plans = 0
        total_profit_distributed = Decimal('0.00')
        total_capital_returned = Decimal('0.00')
        
        for user_plan in active_plans:
            try:
                result = self.process_user_plan(user_plan, now, dry_run)
                if result['profit_added']:
                    profits_processed += 1
                    total_profit_distributed += result['profit_amount']
                if result['matured']:
                    matured_plans += 1
                    total_capital_returned += result['capital_returned']
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing plan {user_plan.id} for {user_plan.user.username}: {str(e)}')
                )
                logger.exception(f'Error processing user plan {user_plan.id}')
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n=== SUMMARY ==='))
        self.stdout.write(f'Active plans processed: {active_plans.count()}')
        self.stdout.write(f'Daily profits distributed: {profits_processed}')
        self.stdout.write(f'Total profit distributed: ${total_profit_distributed}')
        self.stdout.write(f'Plans matured: {matured_plans}')
        self.stdout.write(f'Total capital returned: ${total_capital_returned}')

    @transaction.atomic
    def process_user_plan(self, user_plan, now, dry_run=False):
        """Process a single user's investment plan."""
        result = {
            'profit_added': False,
            'profit_amount': Decimal('0.00'),
            'matured': False,
            'capital_returned': Decimal('0.00'),
        }
        
        plan = user_plan.plan
        user = user_plan.user
        
        # Get or create account
        account, _ = Account.objects.get_or_create(user=user)
        
        # Calculate days since start
        days_elapsed = (now - user_plan.start_date).days
        
        # Check if profit should be added today (once per day)
        time_since_last_profit = now - user_plan.last_profit_at
        should_add_profit = time_since_last_profit >= timedelta(hours=23)  # Allow some buffer
        
        # Check if plan has matured
        is_matured = days_elapsed >= plan.duration_days
        
        self.stdout.write(
            f'\nProcessing: {user.username} - {plan.name}'
            f'\n  Amount: ${user_plan.amount}, Day {days_elapsed}/{plan.duration_days}'
            f'\n  Last profit: {user_plan.last_profit_at}'
        )
        
        # Add daily profit if eligible and not yet matured
        if should_add_profit and not is_matured:
            daily_profit = (user_plan.amount * plan.daily_profit_rate) / Decimal('100')
            
            self.stdout.write(f'  Adding daily profit: ${daily_profit}')
            
            if not dry_run:
                # Add to account balance
                account.balance += daily_profit
                account.save()
                
                # Update user plan
                user_plan.current_profit += daily_profit
                user_plan.last_profit_at = now
                user_plan.save()
                
                # Create transaction record
                Transaction.objects.create(
                    account=account,
                    transaction_type='profit',
                    amount=daily_profit,
                    description=f'Daily profit from {plan.name} (Day {days_elapsed + 1})',
                    status='completed'
                )
            
            result['profit_added'] = True
            result['profit_amount'] = daily_profit
        
        # Handle maturity
        if is_matured and user_plan.is_active:
            self.stdout.write(self.style.WARNING(f'  Plan MATURED after {plan.duration_days} days'))
            
            if not dry_run:
                # Mark plan as inactive
                user_plan.is_active = False
                user_plan.save()
                
                # Return capital if the plan includes capital return
                if plan.capital_return:
                    account.balance += user_plan.amount
                    account.save()
                    
                    Transaction.objects.create(
                        account=account,
                        transaction_type='capital_return',
                        amount=user_plan.amount,
                        description=f'Capital returned from {plan.name}',
                        status='completed'
                    )
                    
                    result['capital_returned'] = user_plan.amount
                    self.stdout.write(self.style.SUCCESS(f'  Capital returned: ${user_plan.amount}'))
            
            result['matured'] = True
        
        return result
