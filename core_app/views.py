from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .forms import UserRegistrationForm, DepositForm, WithdrawalForm
from .models import Account, Transaction, PaymentMethod, Deposit, Withdrawal, Project, Asset, Investment, InvestmentPlan, UserPlan
from .utils import send_transaction_email, send_transaction_request_email

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
    from django.db.models import Sum
    
    account, created = Account.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(account=account).order_by('-timestamp')[:5]
    # Fetch pending deposits and withdrawals
    pending_deposits = Deposit.objects.filter(user=request.user, status='pending').order_by('-created_at')[:3]
    pending_withdrawals = Withdrawal.objects.filter(user=request.user, status='pending').order_by('-created_at')[:3]
    # Fetch active projects and investment plans for the dashboard
    active_projects = Project.objects.filter(status='funding')[:3]
    investment_plans = InvestmentPlan.objects.filter(is_active=True)[:3]
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    
    # Calculate total invested (active investments)
    total_plan_invested = UserPlan.objects.filter(user=request.user, is_active=True).aggregate(total=Sum('amount'))['total'] or 0
    total_project_invested = Investment.objects.filter(user=request.user, status='active').aggregate(total=Sum('amount_invested'))['total'] or 0
    total_invested = total_plan_invested + total_project_invested
    
    # Get user's active investment plans
    from datetime import timedelta
    from decimal import Decimal
    user_active_plans = UserPlan.objects.filter(user=request.user, is_active=True).select_related('plan')
    
    # Calculate maturity date and expected profit for each plan
    user_plans_data = []
    for user_plan in user_active_plans:
        maturity_date = user_plan.start_date + timedelta(days=user_plan.plan.duration_days)
        daily_rate = Decimal(user_plan.plan.daily_profit_rate) / Decimal(100)
        expected_profit = user_plan.amount * daily_rate * user_plan.plan.duration_days
        user_plans_data.append({
            'plan': user_plan,
            'maturity_date': maturity_date,
            'expected_profit': expected_profit,
        })
    
    return render(request, 'dashboard.html', {
        'account': account,
        'recent_transactions': transactions,
        'pending_deposits': pending_deposits,
        'pending_withdrawals': pending_withdrawals,
        'active_projects': active_projects,
        'investment_plans': investment_plans,
        'payment_methods': payment_methods,
        'total_invested': total_invested,
        'user_active_plans': user_plans_data
    })

@login_required
def investment_plan(request):
    account = request.user.account
    projects = Project.objects.filter(status='funding')
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    return render(request, 'investment-plan.html', {
        'projects': projects,
        'payment_methods': payment_methods,
        'account': account
    })

@login_required
def shares(request):
    tdi_share = Asset.objects.filter(ticker='TDI').first()
    other_assets = Asset.objects.exclude(ticker='TDI')
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    account = request.user.account
    return render(request, 'shares.html', {
        'tdi_share': tdi_share,
        'other_assets': other_assets,
        'payment_methods': payment_methods,
        'account': account
    })

@login_required
def buy_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0').replace(',', '')
        try:
            from decimal import Decimal
            amount = Decimal(amount_str)
        except:
            messages.error(request, "Invalid amount.")
            return redirect('investment_plan')

        account = request.user.account
        payment_method_id = request.POST.get('payment_method')
        
        if amount < project.min_investment:
            messages.error(request, f"Minimum investment for this project is ${project.min_investment}")
            return redirect(request.META.get('HTTP_REFERER', 'investment_plan'))

        # Flow 1: Use Account Balance
        if not payment_method_id or payment_method_id == 'balance':
            if account.balance >= amount:
                with transaction.atomic():
                    Investment.objects.create(
                        user=request.user,
                        project=project,
                        amount_invested=amount,
                        purchase_price=amount,
                        status='active'
                    )
                    
                    import time
                    Transaction.objects.create(
                        account=account,
                        transaction_type='withdrawal',
                        amount=amount,
                        description=f"Investment in Project: {project.title}",
                        status='completed',
                        reference=f"INV-PRJ-{project.id}-{request.user.id}-{int(time.time())}"
                    )
                    account.balance -= amount
                    account.save()
                messages.success(request, f"Successfully invested ${amount} in {project.title}")
                return redirect('dashboard')
            else:
                messages.error(request, "Insufficient balance. Please deposit funds or choose a direct payment method.")
                return redirect(request.META.get('HTTP_REFERER', 'investment_plan'))
        
        # Flow 2: Direct Deposit & Invest
        else:
            payment_method = get_object_or_404(PaymentMethod, id=payment_method_id)
            deposit = Deposit.objects.create(
                user=request.user,
                payment_method=payment_method,
                amount=amount,
                linked_project=project,
                invest_amount=amount,
                status='pending'
            )
            return redirect('deposit_pay', deposit_id=deposit.id)

    return redirect('investment_plan')

@login_required
def buy_asset(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0').replace(',', '')
        try:
            from decimal import Decimal
            amount = Decimal(amount_str)
        except:
            messages.error(request, "Invalid amount.")
            return redirect('shares')

        account = request.user.account
        payment_method_id = request.POST.get('payment_method')
        
        # Flow 1: Use Account Balance
        if not payment_method_id or payment_method_id == 'balance':
            if account.balance >= amount:
                with transaction.atomic():
                    units = amount / asset.current_price
                    Investment.objects.create(
                        user=request.user,
                        asset=asset,
                        amount_invested=amount,
                        units=units,
                        purchase_price=asset.current_price,
                        status='active'
                    )
                    
                    import time
                    Transaction.objects.create(
                        account=account,
                        transaction_type='withdrawal',
                        amount=amount,
                        description=f"Investment in Asset: {asset.name}",
                        status='completed',
                        reference=f"INV-AST-{asset.id}-{request.user.id}-{int(time.time())}"
                    )
                    account.balance -= amount
                    account.save()
                messages.success(request, f"Successfully invested ${amount} in {asset.name}")
                return redirect('dashboard')
            else:
                messages.error(request, "Insufficient balance. Please deposit funds or choose a direct payment method.")
                return redirect(request.META.get('HTTP_REFERER', 'shares'))
        
        # Flow 2: Direct Deposit & Invest
        else:
            payment_method = get_object_or_404(PaymentMethod, id=payment_method_id)
            deposit = Deposit.objects.create(
                user=request.user,
                payment_method=payment_method,
                amount=amount,
                linked_asset=asset,
                invest_amount=amount,
                status='pending'
            )
            return redirect('deposit_pay', deposit_id=deposit.id)

    return redirect('shares')
@login_required
def investment_packages(request):
    account = request.user.account
    packages = InvestmentPlan.objects.filter(is_active=True)
    active_user_plans = UserPlan.objects.filter(user=request.user, is_active=True)
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    return render(request, 'investment-packages.html', {
        'packages': packages,
        'active_user_plans': active_user_plans,
        'payment_methods': payment_methods,
        'account': account
    })

@login_required
def buy_package(request, package_id):
    package = get_object_or_404(InvestmentPlan, id=package_id)
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0').replace(',', '')
        try:
            from decimal import Decimal
            amount = Decimal(amount_str)
        except:
            messages.error(request, "Invalid amount.")
            return redirect('investment_packages')

        account = request.user.account
        payment_method_id = request.POST.get('payment_method')
        
        if amount < package.min_price or amount > package.max_price:
            messages.error(request, f"Investment must be between ${package.min_price} and ${package.max_price}")
            return redirect(request.META.get('HTTP_REFERER', 'investment_packages'))

        # Flow 1: Use Account Balance
        if not payment_method_id or payment_method_id == 'balance':
            if account.balance >= amount:
                with transaction.atomic():
                    UserPlan.objects.create(
                        user=request.user,
                        plan=package,
                        amount=amount,
                        is_active=True
                    )
                    
                    import time
                    Transaction.objects.create(
                        account=account,
                        transaction_type='withdrawal',
                        amount=amount,
                        description=f"Investment in Plan: {package.name}",
                        status='completed',
                        reference=f"INV-PLN-{package.id}-{request.user.id}-{int(time.time())}"
                    )
                    account.balance -= amount
                    account.save()
                messages.success(request, f"Successfully invested ${amount} in {package.name} plan")
                return redirect('dashboard')
            else:
                messages.error(request, "Insufficient balance. Please deposit funds or choose a direct payment method.")
                return redirect(request.META.get('HTTP_REFERER', 'investment_packages'))
        
        # Flow 2: Direct Deposit & Invest
        else:
            payment_method = get_object_or_404(PaymentMethod, id=payment_method_id)
            deposit = Deposit.objects.create(
                user=request.user,
                payment_method=payment_method,
                amount=amount,
                linked_plan=package,
                invest_amount=amount,
                status='pending'
            )
            return redirect('deposit_pay', deposit_id=deposit.id)

    return redirect('investment_packages')

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
            
            send_transaction_request_email(request.user, 'deposit', amount)
            
            messages.success(request, f"Deposit request for {amount} submitted. It will be credited once confirmed.")
            return redirect('dashboard')
    else:
        form = DepositForm()
    
    return render(request, 'deposit.html', {
        'form': form, 
        'payment_methods': payment_methods
    })

@login_required
def deposit_pay(request, deposit_id):
    """Show payment details for a pending deposit (linked investment flow)."""
    deposit_obj = get_object_or_404(Deposit, id=deposit_id, user=request.user)
    
    if deposit_obj.status != 'pending':
        messages.info(request, "This deposit has already been processed.")
        return redirect('dashboard')
    
    return render(request, 'deposit_pay.html', {
        'deposit': deposit_obj,
        'payment_method': deposit_obj.payment_method
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
            
            withdrawal_obj = Withdrawal.objects.create(
                user=request.user,
                amount=amount,
                wallet_name=wallet_name,
                wallet_address=wallet_address,
                network=network,
                status='pending'
            )
            
            send_transaction_request_email(request.user, 'withdrawal', amount, withdrawal=withdrawal_obj)
            
            messages.success(request, f"Withdrawal request for {amount} submitted. It will be processed shortly.")
            return redirect('dashboard')
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = WithdrawalForm()
    
    return render(request, 'withdrawal.html', {'form': form, 'account': account})
