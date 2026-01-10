from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Account, Transaction, Project, Investment, Deposit, PaymentMethod, Withdrawal, InvestmentPlan, UserPlan
from django.core.management import call_command
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

class WithdrawalWalletNameTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password', first_name='Test')
        self.account = self.user.account
        self.account.balance = 1000
        self.account.save()
        self.client = Client()
        self.client.login(username='testuser', password='password')

    def test_withdrawal_str_with_wallet_name(self):
        from decimal import Decimal
        withdrawal = Withdrawal.objects.create(
            user=self.user,
            amount=Decimal('100.00'),
            wallet_name='My Wallet',
            wallet_address='addr123',
            network='TRC20'
        )
        self.assertIn('(My Wallet)', str(withdrawal))

    def test_withdrawal_str_without_wallet_name(self):
        from decimal import Decimal
        withdrawal = Withdrawal.objects.create(
            user=self.user,
            amount=Decimal('100.00'),
            wallet_address='addr123',
            network='TRC20'
        )
        # Check if it starts with the expected base string
        current_str = str(withdrawal)
        self.assertTrue(current_str.startswith('Withdrawal 100'))
        self.assertIn(self.user.username, current_str)
        self.assertIn('(pending)', current_str)

    def test_withdrawal_signal_creates_transaction_with_wallet_name(self):
        withdrawal = Withdrawal.objects.create(
            user=self.user,
            amount=100,
            wallet_name='My Wallet',
            wallet_address='addr123',
            network='TRC20'
        )
        # Manually trigger signal by updating status to completed
        withdrawal.status = 'completed'
        withdrawal.save()

        txn = Transaction.objects.filter(account=self.account, transaction_type='withdrawal').last()
        self.assertIsNotNone(txn)
        self.assertIn('(My Wallet)', txn.description)

    def test_withdrawal_view_saves_wallet_name(self):
        response = self.client.post(reverse('withdrawal'), {
            'amount': '50.00',
            'wallet_name': 'Binance Wallet',
            'wallet_address': '0x123',
            'network': 'ERC20'
        })
        self.assertEqual(response.status_code, 302) # Redirect to dashboard
        
        withdrawal = Withdrawal.objects.filter(user=self.user).last()
        self.assertEqual(withdrawal.wallet_name, 'Binance Wallet')
        self.assertEqual(float(withdrawal.amount), 50.00)

    def test_buy_project_success(self):
        project = Project.objects.create(
            title="Drilling Rig A",
            min_investment=500,
            return_rate=15,
            duration_days=30,
            status='funding'
        )
        response = self.client.post(reverse('buy_project', args=[project.id]), {
            'amount': '600.00'
        })
        self.assertEqual(response.status_code, 302)
        
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.balance), 400.00) # 1000 - 600
        
        self.assertTrue(Transaction.objects.filter(account=self.account, transaction_type='withdrawal').exists())
        self.assertTrue(Investment.objects.filter(user=self.user, project=project).exists())

    def test_buy_project_insufficient_funds(self):
        project = Project.objects.create(
            title="Expensive Rig",
            min_investment=2000,
            return_rate=20,
            duration_days=60,
            status='funding'
        )
        response = self.client.post(reverse('buy_project', args=[project.id]), {
            'amount': '2000.00'
        })
        self.assertEqual(response.status_code, 302)
        
        self.account.refresh_from_db()
        self.assertEqual(float(self.account.balance), 1000.00) # Unchanged

    def test_deposit_and_invest_automation(self):
        project = Project.objects.create(
            title="Automated Rig",
            min_investment=500,
            return_rate=20,
            duration_days=30,
            status='funding'
        )
        payment_method = PaymentMethod.objects.create(name="BTC", is_active=True)
        
        # Create a linked deposit
        deposit = Deposit.objects.create(
            user=self.user,
            payment_method=payment_method,
            amount=600,
            linked_project=project,
            invest_amount=600,
            status='pending'
        )
        
        # Manually mark as completed (simulating admin)
        deposit.status = 'completed'
        deposit.save() # This triggers the signal
        
        self.account.refresh_from_db()
        # Balance should be 1000 + 600 - 600 = 1000
        self.assertEqual(float(self.account.balance), 1000.00)
        
        # Check if investment exists
        self.assertTrue(Investment.objects.filter(user=self.user, project=project, amount_invested=600).exists())
        
        # Check if transactions exist (1 deposit, 1 withdrawal)
        self.assertTrue(Transaction.objects.filter(account=self.account, transaction_type='deposit', amount=600).exists())
        self.assertTrue(Transaction.objects.filter(account=self.account, transaction_type='withdrawal', amount=600).exists())

    def test_investment_plan_automation(self):
        # 1. Create a Plan
        plan = InvestmentPlan.objects.create(
            name="Starter Plan",
            short_description="Test plan",
            min_price=100,
            max_price=1000,
            daily_profit_rate=2.00, # 2% daily
            duration_days=2,
            capital_return=True
        )
        
        # 2. Create a UserPlan (invested $500)
        # We'll set the last_profit_at to 25 hours ago to trigger the command
        start_time = timezone.now() - timedelta(hours=25)
        user_plan = UserPlan.objects.create(
            user=self.user,
            plan=plan,
            amount=500,
            start_date=start_time,
            last_profit_at=start_time,
            is_active=True
        )
        
        initial_balance = float(self.account.balance)
        
        # 3. Run the management command
        call_command('update_profits')
        
        self.account.refresh_from_db()
        user_plan.refresh_from_db()
        
        # Profit should be 500 * 0.02 = 10
        expected_balance = initial_balance + 10.0
        self.assertEqual(float(self.account.balance), expected_balance)
        self.assertEqual(float(user_plan.current_profit), 10.0)
        
        # Check Transaction
        self.assertTrue(Transaction.objects.filter(account=self.account, transaction_type='profit', amount=10).exists())
        
        # 4. Test Capital Return (Plan ends after 2 days)
        # Set start_date to 3 days ago
        user_plan.start_date = timezone.now() - timedelta(days=3)
        user_plan.last_profit_at = timezone.now() - timedelta(hours=25)
        user_plan.save()
        
        call_command('update_profits')
        
        self.account.refresh_from_db()
        user_plan.refresh_from_db()
        
        # Should have received another profit and the capital ($500)
        # New balance: expected_balance + 10 (profit) + 500 (capital) = initial + 20 + 500
        final_expected = initial_balance + 10 + 10 + 500
        self.assertEqual(float(self.account.balance), final_expected)
        self.assertFalse(user_plan.is_active)
        
        # Check Capital Return Transaction
        self.assertTrue(Transaction.objects.filter(account=self.account, transaction_type='capital_return', amount=500).exists())
