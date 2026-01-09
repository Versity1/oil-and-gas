from django.db import models
from django.contrib.auth.models import User
import uuid

class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    account_number = models.CharField(max_length=12, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.account_number:
            # Generate a simple 10-digit account number
            self.account_number = str(uuid.uuid4().int)[:10]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username}'s Account - {self.account_number}"

class PaymentMethod(models.Model):
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)
    network = models.CharField(max_length=50)
    wallet_address = models.CharField(max_length=255)
    qr_code = models.ImageField(upload_to='payment_methods/qr_codes/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='payment_methods/thumbnails/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.network})"

class Deposit(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposits')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_hash = models.CharField(max_length=255, blank=True, null=True, help_text="User provided proof of payment")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Deposit {self.amount} - {self.user.username} ({self.status})"

class Withdrawal(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    wallet_name = models.CharField(max_length=100, blank=True, null=True, help_text="Optional name for your wallet")
    wallet_address = models.CharField(max_length=255)
    network = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        wallet_info = f" ({self.wallet_name})" if self.wallet_name else ""
        return f"Withdrawal {self.amount}{wallet_info} - {self.user.username} ({self.status})"

class Project(models.Model):
    STATUS_CHOICES = (
        ('funding', 'Funding'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    min_investment = models.DecimalField(max_digits=12, decimal_places=2)
    return_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage return (e.g. 15.00)")
    duration_days = models.IntegerField(help_text="Duration in days")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='funding')
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Asset(models.Model):
    ASSET_TYPES = (
        ('share', 'Share'),
        ('bond', 'Bond'),
    )

    name = models.CharField(max_length=100)
    ticker = models.CharField(max_length=10, unique=True)
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPES)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    previous_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="For Bonds")
    maturity_date = models.DateField(blank=True, null=True, help_text="For Bonds")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.ticker})"

    @property
    def growth_percentage(self):
        if self.previous_price and self.previous_price > 0:
            growth = ((self.current_price - self.previous_price) / self.previous_price) * 100
            return round(growth, 2)
        return 0

class Investment(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('matured', 'Matured'),
        ('sold', 'Sold'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, blank=True, null=True)
    amount_invested = models.DecimalField(max_digits=12, decimal_places=2)
    units = models.DecimalField(max_digits=12, decimal_places=4, default=1.0)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.project.title if self.project else self.asset.name
        return f"{self.user.username} - {target} ({self.amount_invested})"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    timestamp = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=50, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = str(uuid.uuid4().hex[:12].upper())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} ({self.account.user.username})"
