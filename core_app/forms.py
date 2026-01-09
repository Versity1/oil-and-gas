from django import forms
from django.contrib.auth.models import User

class UserRegistrationForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'John Doe'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'name@techodrill.com'})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        required=True
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        required=True
    )
    terms = forms.BooleanField(required=True)

    class Meta:
        model = User
        fields = ("email", "full_name")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        # Split full_name into first and last name if possible, or just use first_name
        name_parts = self.cleaned_data["full_name"].split(' ', 1)
        user.first_name = name_parts[0]
        if len(name_parts) > 1:
            user.last_name = name_parts[1]
        
        user.set_password(self.cleaned_data["password1"])
        
        if commit:
            user.save()
        return user

from .models import PaymentMethod

class TransactionForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        min_value=1.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'})
    )

class DepositForm(TransactionForm):
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        widget=forms.RadioSelect(attrs={'class': 'hidden'}),
        required=True
    )
    transaction_hash = forms.CharField(
        max_length=255, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Paste transaction hash/ID'})
    )

class WithdrawalForm(TransactionForm):
    wallet_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Wallet Name (e.g. My Binance)'})
    )
    wallet_address = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your wallet address'})
    )
    network = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Network (e.g. TRC20, ERC20)'})
    )

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.account and amount > self.account.balance:
            raise forms.ValidationError(f"Insufficient funds. Your current balance is {self.account.balance}")
        return amount
