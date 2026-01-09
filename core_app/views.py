from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .forms import UserRegistrationForm, DepositForm, WithdrawalForm
from .models import Account, Transaction, PaymentMethod, Deposit, Withdrawal
from .utils import send_transaction_email

# Front Pages
def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def services(request):
    return render(request, 'services.html')

def contact(request):
    return render(request, 'contact.html')

def products(request):
    return render(request, 'products.html')

# Auth Pages
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful. Welcome to the dashboard!")
            return redirect('dashboard')
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('home')

# Dashboard Pages
@login_required
def dashboard(request):
    account, created = Account.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(account=account).order_by('-timestamp')[:5]
    return render(request, 'dashboard.html', {
        'account': account,
        'recent_transactions': transactions
    })

@login_required
def investment_plan(request):
    account = request.user.account
    return render(request, 'investment-plan.html', {'account': account})

@login_required
def shares(request):
    account = request.user.account
    return render(request, 'shares.html', {'account': account})

@login_required
def transaction_history(request):
    account = request.user.account
    # Realized transactions (Ledger)
    ledger = Transaction.objects.filter(account=account).order_by('-timestamp')
    
    # Pending requests
    pending_deposits = Deposit.objects.filter(user=request.user, status='pending')
    pending_withdrawals = Withdrawal.objects.filter(user=request.user, status='pending')
    
    return render(request, 'transaction-history.html', {
        'transactions': ledger,
        'pending_deposits': pending_deposits,
        'pending_withdrawals': pending_withdrawals
    })

@login_required
def deposit(request):
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            payment_method = form.cleaned_data['payment_method']
            txn_hash = form.cleaned_data['transaction_hash']
            
            Deposit.objects.create(
                user=request.user,
                payment_method=payment_method,
                amount=amount,
                transaction_hash=txn_hash,
                status='pending'
            )
            
            messages.success(request, f"Deposit request for {amount} submitted. It will be credited once confirmed.")
            return redirect('dashboard')
    else:
        form = DepositForm()
    
    return render(request, 'deposit.html', {
        'form': form, 
        'payment_methods': payment_methods
    })

@login_required
def withdrawal(request):
    account = request.user.account
    if request.method == 'POST':
        form = WithdrawalForm(request.POST, account=account)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            wallet_address = form.cleaned_data['wallet_address']
            network = form.cleaned_data['network']
            
            Withdrawal.objects.create(
                user=request.user,
                amount=amount,
                wallet_address=wallet_address,
                network=network,
                status='pending'
            )
            
            messages.success(request, f"Withdrawal request for {amount} submitted. It will be processed shortly.")
            return redirect('dashboard')
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = WithdrawalForm()
    
    return render(request, 'withdrawal.html', {'form': form, 'account': account})
