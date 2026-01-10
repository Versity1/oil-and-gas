"""
Management command to process matured investments and complete payouts.
Run this command daily via cron job: python manage.py process_investment_completions
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from core_app.models import Investment, UserPlan, Account, Transaction
from core_app.utils import send_investment_email


class Command(BaseCommand):
    help = 'Process matured investments and complete payouts for projects and plans'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be processed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        now = timezone.now()
        
        # Process matured project investments
        project_completions = self.process_project_investments(now, dry_run)
        
        # Process matured plan investments
        plan_completions = self.process_plan_investments(now, dry_run)
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] Would complete {project_completions} project investments and {plan_completions} plan investments'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Completed {project_completions} project investments and {plan_completions} plan investments'))

    def process_project_investments(self, now, dry_run):
        """Process matured project investments and payout to users."""
        completed_count = 0
        
        # Get all active project investments
        active_project_investments = Investment.objects.filter(
            project__isnull=False,
            status='active'
        ).select_related('user', 'project', 'user__account')
        
        for investment in active_project_investments:
            # Calculate maturity date
            maturity_date = investment.created_at + timedelta(days=investment.project.duration_days)
            
            if now >= maturity_date:
                if dry_run:
                    self.stdout.write(f'  Would complete investment: {investment.user.username} - {investment.project.title} (${investment.amount_invested})')
                    completed_count += 1
                    continue
                
                # Calculate payout
                return_rate = Decimal(investment.project.return_rate) / Decimal(100)
                profit = investment.amount_invested * return_rate
                total_payout = investment.amount_invested + profit  # Principal + Profit
                
                with transaction.atomic():
                    # Mark investment as matured
                    investment.status = 'matured'
                    investment.save()
                    
                    # Credit user's account
                    account = investment.user.account
                    account.balance += total_payout
                    account.save()
                    
                    # Create transaction record for profit
                    Transaction.objects.create(
                        account=account,
                        transaction_type='profit',
                        amount=profit,
                        description=f"Project Profit: {investment.project.title}",
                        status='completed',
                        reference=f"PROJ-PRF-{investment.project.id}-{investment.user.id}-{int(now.timestamp())}"
                    )
                    
                    # Create transaction record for capital return
                    Transaction.objects.create(
                        account=account,
                        transaction_type='capital_return',
                        amount=investment.amount_invested,
                        description=f"Capital Return: {investment.project.title}",
                        status='completed',
                        reference=f"PROJ-CAP-{investment.project.id}-{investment.user.id}-{int(now.timestamp())}"
                    )
                    
                    # Send email notification
                    try:
                        self._send_completion_email(
                            investment.user,
                            'project',
                            investment.project.title,
                            investment.amount_invested,
                            profit,
                            total_payout
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Failed to send email: {e}'))
                
                completed_count += 1
                self.stdout.write(f'  ✓ Completed: {investment.user.username} - {investment.project.title} (+${total_payout})')
        
        return completed_count

    def process_plan_investments(self, now, dry_run):
        """Process matured plan investments and payout to users."""
        completed_count = 0
        
        # Get all active user plans
        active_plans = UserPlan.objects.filter(
            is_active=True
        ).select_related('user', 'plan', 'user__account')
        
        for user_plan in active_plans:
            # Calculate maturity date
            maturity_date = user_plan.start_date + timedelta(days=user_plan.plan.duration_days)
            
            if now >= maturity_date:
                if dry_run:
                    self.stdout.write(f'  Would complete plan: {user_plan.user.username} - {user_plan.plan.name} (${user_plan.amount})')
                    completed_count += 1
                    continue
                
                # Calculate final payout
                daily_rate = Decimal(user_plan.plan.daily_profit_rate) / Decimal(100)
                expected_profit = user_plan.amount * daily_rate * user_plan.plan.duration_days
                
                # Use current_profit if accumulated, otherwise use expected
                final_profit = max(user_plan.current_profit, expected_profit)
                
                # Total payout includes capital if capital_return is True
                capital_return = user_plan.amount if user_plan.plan.capital_return else Decimal(0)
                total_payout = final_profit + capital_return
                
                with transaction.atomic():
                    # Mark plan as inactive (completed)
                    user_plan.is_active = False
                    user_plan.save()
                    
                    # Credit user's account
                    account = user_plan.user.account
                    account.balance += total_payout
                    account.save()
                    
                    # Create transaction record for profit if any
                    if final_profit > 0:
                        Transaction.objects.create(
                            account=account,
                            transaction_type='profit',
                            amount=final_profit,
                            description=f"Plan Maturity Profit: {user_plan.plan.name}",
                            status='completed',
                            reference=f"PLAN-PRF-{user_plan.plan.id}-{user_plan.user.id}-{int(now.timestamp())}"
                        )
                    
                    # Create transaction record for capital return if applicable
                    if capital_return > 0:
                        Transaction.objects.create(
                            account=account,
                            transaction_type='capital_return',
                            amount=capital_return,
                            description=f"Capital Return: {user_plan.plan.name}",
                            status='completed',
                            reference=f"PLAN-CAP-{user_plan.plan.id}-{user_plan.user.id}-{int(now.timestamp())}"
                        )
                    
                    # Send email notification
                    try:
                        self._send_completion_email(
                            user_plan.user,
                            'plan',
                            user_plan.plan.name,
                            user_plan.amount,
                            final_profit,
                            total_payout
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Failed to send email: {e}'))
                
                completed_count += 1
                self.stdout.write(f'  ✓ Completed: {user_plan.user.username} - {user_plan.plan.name} (+${total_payout})')
        
        return completed_count

    def _send_completion_email(self, user, investment_type, name, principal, profit, total):
        """Send investment completion email to user."""
        from django.core.mail import send_mail
        from django.conf import settings
        
        type_labels = {
            'project': 'Project Investment',
            'plan': 'Investment Plan'
        }
        
        subject = f"🎉 Investment Matured: {name}"
        
        message = f"""
Dear {user.first_name or user.username},

Congratulations! Your investment has matured and the funds have been credited to your account.

Investment Details:
- Type: {type_labels.get(investment_type, 'Investment')}
- Name: {name}
- Principal: ${principal:,.2f}
- Profit Earned: ${profit:,.2f}
- Total Payout: ${total:,.2f}

Your updated account balance is: ${user.account.balance:,.2f}

Thank you for investing with Techodrill Oil and Gas. We look forward to helping you grow your wealth!

Best regards,
The Techodrill Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@techodrill.com',
            [user.email],
            fail_silently=False,
        )
