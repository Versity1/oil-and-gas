from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .forms import UserRegistrationForm, DepositForm, WithdrawalForm
from .models import Account, Transaction
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
    transactions = Transaction.objects.filter(account=account).order_by('-timestamp')
    return render(request, 'transaction-history.html', {'transactions': transactions})

@login_required
def deposit(request):
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            
            with transaction.atomic():
                account = request.user.account
                account.balance += amount
                account.save()
                
                txn = Transaction.objects.create(
                    account=account,
                    transaction_type='deposit',
                    amount=amount,
                    description=description or 'Account Deposit',
                    status='completed'
                )
            
            # Send email notification
            send_transaction_email(request.user, txn)
            
            messages.success(request, f"Successfully deposited {amount}. Your new balance is {account.balance}.")
            return redirect('dashboard')
    else:
        form = DepositForm()
    
    return render(request, 'deposit.html', {'form': form})

@login_required
def withdrawal(request):
    account = request.user.account
    if request.method == 'POST':
        form = WithdrawalForm(request.POST, account=account)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            
            if account.balance >= amount:
                with transaction.atomic():
                    account.balance -= amount
                    account.save()
                    
                    txn = Transaction.objects.create(
                        account=account,
                        transaction_type='withdrawal',
                        amount=amount,
                        description=description or 'Account Withdrawal',
                        status='completed'
                    )
                
                # Send email notification
                send_transaction_email(request.user, txn)
                
                messages.success(request, f"Successfully withdrawn {amount}. Your new balance is {account.balance}.")
                return redirect('dashboard')
            else:
                messages.error(request, "Insufficient funds.")
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = WithdrawalForm()
    
    return render(request, 'withdrawal.html', {'form': form, 'account': account})