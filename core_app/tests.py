from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Account, Withdrawal, PaymentMethod, Transaction
from django.urls import reverse

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
