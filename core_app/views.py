from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .forms import UserRegistrationForm, DepositForm, WithdrawalForm
from .models import Account, Transaction, PaymentMethod, Deposit, Withdrawal, Project, Asset, Investment
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
    projects = Project.objects.filter(status__in=['funding', 'active'])
    return render(request, 'investment-plan.html', {
        'account': account,
        'projects': projects
    })

@login_required
def shares(request):
    account = request.user.account
    # Fetch TDI share (assuming it's the main one)
    tdi_share = Asset.objects.filter(ticker='TDI', asset_type='share').first()
    # Fetch other assets
    other_assets = Asset.objects.filter(is_active=True).exclude(ticker='TDI')
    return render(request, 'shares.html', {
        'account': account,
        'tdi_share': tdi_share,
        'other_assets': other_assets
    })

@login_required
def buy_project(request, project_id):
    if request.method == 'POST':
        project = get_object_or_404(Project, id=project_id)
        amount_str = request.POST.get('amount', '0').replace(',', '')
        try:
            from decimal import Decimal
            amount = Decimal(amount_str)
        except:
            messages.error(request, "Invalid amount.")
            return redirect('investment_plan')

        account = request.user.account
        
        if amount < project.min_investment:
            messages.error(request, f"Minimum investment for this project is ${project.min_investment}")
            return redirect('investment_plan')
            
        if account.balance >= amount:
            with transaction.atomic():
                account.balance -= amount
                account.save()
                
                Investment.objects.create(
                    user=request.user,
                    project=project,
                    amount_invested=amount,
                    purchase_price=amount,
                    status='active'
                )
                
                Transaction.objects.create(
                    account=account,
                    transaction_type='withdrawal',
                    amount=amount,
                    description=f"Investment in Project: {project.title}",
                    status='completed',
                    reference=f"INV-PRJ-{project.id}-{request.user.id}-{transaction.get_connection().connection.get_server_version() if hasattr(transaction.get_connection(), 'connection') else ''}"[:100] # Simplistic unique ref
                )
            messages.success(request, f"Successfully invested ${amount} in {project.title}")
        else:
            messages.error(request, "Insufficient funds.")
    return redirect('investment_plan')

@login_required
def buy_asset(request, asset_id):
    if request.method == 'POST':
        asset = get_object_or_404(Asset, id=asset_id)
        amount_str = request.POST.get('amount', '0').replace(',', '')
        try:
            from decimal import Decimal
            amount = Decimal(amount_str)
        except:
            messages.error(request, "Invalid amount.")
            return redirect('shares')

        account = request.user.account
        
        if account.balance >= amount:
            with transaction.atomic():
                units = amount / asset.current_price
                account.balance -= amount
                account.save()
                
                Investment.objects.create(
                    user=request.user,
                    asset=asset,
                    amount_invested=amount,
                    units=units,
                    purchase_price=asset.current_price,
                    status='active'
                )
                
                Transaction.objects.create(
                    account=account,
                    transaction_type='withdrawal',
                    amount=amount,
                    description=f"Purchased {units:.4f} units of {asset.ticker}",
                    status='completed',
                    reference=f"INV-AST-{asset.id}-{request.user.id}"
                )
            messages.success(request, f"Successfully purchased {units:.4f} units of {asset.name}")
        else:
            messages.error(request, "Insufficient funds.")
    return redirect('shares')

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
            wallet_name = form.cleaned_data.get('wallet_name')
            wallet_address = form.cleaned_data['wallet_address']
            network = form.cleaned_data['network']
            
            Withdrawal.objects.create(
                user=request.user,
                amount=amount,
                wallet_name=wallet_name,
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
