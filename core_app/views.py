from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from .forms import UserRegistrationForm, DepositForm, WithdrawalForm
from .models import Account, Transaction, PaymentMethod, Deposit, Withdrawal, Project, Asset, Investment, InvestmentPlan, UserPlan, Notification
from .utils import send_transaction_email, send_transaction_request_email, send_investment_email

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
    from datetime import timedelta
    from decimal import Decimal
    
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
    
    # Get user's active investment plans with maturity and expected profit
    user_active_plans = UserPlan.objects.filter(user=request.user, is_active=True).select_related('plan')
    user_plans_data = []
    for user_plan in user_active_plans:
        maturity_date = user_plan.start_date + timedelta(days=user_plan.plan.duration_days)
        daily_rate = Decimal(user_plan.plan.daily_profit_rate) / Decimal(100)
        expected_profit = user_plan.amount * daily_rate * user_plan.plan.duration_days
        expected_total = user_plan.amount + expected_profit if user_plan.plan.capital_return else expected_profit
        user_plans_data.append({
            'plan': user_plan,
            'maturity_date': maturity_date,
            'expected_profit': expected_profit,
            'expected_total': expected_total,
            'current_profit': user_plan.current_profit,
        })
    
    # Get user's project investments with maturity and expected income
    project_investments = Investment.objects.filter(
        user=request.user, 
        project__isnull=False,
        status='active'
    ).select_related('project')
    
    project_investments_data = []
    for inv in project_investments:
        maturity_date = inv.created_at + timedelta(days=inv.project.duration_days)
        return_rate = Decimal(inv.project.return_rate) / Decimal(100)
        expected_profit = inv.amount_invested * return_rate
        expected_total = inv.amount_invested + expected_profit
        
        project_investments_data.append({
            'investment': inv,
            'project': inv.project,
            'amount_invested': inv.amount_invested,
            'maturity_date': maturity_date,
            'expected_profit': expected_profit,
            'expected_total': expected_total,
            'type': 'project',
        })
    
    # Get user's asset investments (shares/bonds) with current value
    asset_investments = Investment.objects.filter(
        user=request.user,
        asset__isnull=False,
        status='active'
    ).select_related('asset')
    
    asset_investments_data = []
    for inv in asset_investments:
        current_value = inv.units * inv.asset.current_price
        unrealized_gain = current_value - inv.amount_invested
        gain_percent = (unrealized_gain / inv.amount_invested * 100) if inv.amount_invested > 0 else Decimal(0)
        
        # For bonds, calculate maturity and interest
        if inv.asset.asset_type == 'bond' and inv.asset.maturity_date:
            maturity_date = inv.asset.maturity_date
            interest_rate = Decimal(inv.asset.interest_rate or 0) / Decimal(100)
            expected_interest = inv.amount_invested * interest_rate
            expected_total = inv.amount_invested + expected_interest
        else:
            maturity_date = None
            expected_interest = None
            expected_total = current_value
        
        asset_investments_data.append({
            'investment': inv,
            'asset': inv.asset,
            'amount_invested': inv.amount_invested,
            'units': inv.units,
            'purchase_price': inv.purchase_price,
            'current_price': inv.asset.current_price,
            'current_value': current_value,
            'unrealized_gain': unrealized_gain,
            'gain_percent': gain_percent,
            'maturity_date': maturity_date,
            'expected_interest': expected_interest,
            'expected_total': expected_total,
            'type': inv.asset.asset_type,
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
        'user_active_plans': user_plans_data,
        'project_investments': project_investments_data,
        'asset_investments': asset_investments_data,
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
    from django.db.models import Sum
    from decimal import Decimal
    
    tdi_share = Asset.objects.filter(ticker='TDI').first()
    all_assets = Asset.objects.filter(is_active=True)
    other_assets = all_assets.exclude(ticker='TDI')
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    account = request.user.account
    
    # Get user's asset holdings
    user_holdings = Investment.objects.filter(
        user=request.user, 
        asset__isnull=False, 
        status='active'
    ).select_related('asset')
    
    # Calculate portfolio stats
    total_invested = user_holdings.aggregate(total=Sum('amount_invested'))['total'] or Decimal('0')
    
    # Calculate current value based on current prices
    portfolio_value = Decimal('0')
    holdings_data = []
    for holding in user_holdings:
        current_value = holding.units * holding.asset.current_price
        unrealized_gain = current_value - holding.amount_invested
        holdings_data.append({
            'holding': holding,
            'current_value': current_value,
            'unrealized_gain': unrealized_gain,
            'gain_percent': (unrealized_gain / holding.amount_invested * 100) if holding.amount_invested > 0 else 0
        })
        portfolio_value += current_value
    
    total_gain = portfolio_value - total_invested
    
    return render(request, 'shares.html', {
        'tdi_share': tdi_share,
        'all_assets': all_assets,
        'other_assets': other_assets,
        'payment_methods': payment_methods,
        'account': account,
        'user_holdings': holdings_data,
        'total_invested': total_invested,
        'portfolio_value': portfolio_value,
        'total_gain': total_gain
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
                
                # Send investment confirmation email
                send_investment_email(
                    user=request.user,
                    investment_type='project',
                    investment_name=project.title,
                    amount=amount
                )
                
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
                
                # Send investment confirmation email
                send_investment_email(
                    user=request.user,
                    investment_type='share',
                    investment_name=asset.name,
                    amount=amount,
                    units=units,
                    price=asset.current_price
                )
                
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
                
                # Send investment confirmation email
                send_investment_email(
                    user=request.user,
                    investment_type='plan',
                    investment_name=package.name,
                    amount=amount
                )
                
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


@login_required
def transfer_to_main(request):
    """Transfer funds from trading balance to main balance."""
    if request.method == 'POST':
        account = request.user.account
        amount_str = request.POST.get('amount', '0').replace(',', '')
        
        try:
            from decimal import Decimal
            amount = Decimal(amount_str)
            
            if amount <= 0:
                messages.error(request, "Please enter a valid amount.")
                return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
            
            if amount > account.trading_balance:
                messages.error(request, f"Insufficient trading balance. Available: ${account.trading_balance}")
                return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
            
            with transaction.atomic():
                account.trading_balance -= amount
                account.balance += amount
                account.save()
                
                # Create transaction record
                Transaction.objects.create(
                    account=account,
                    transaction_type='deposit',
                    amount=amount,
                    description="Transfer from Trading Wallet",
                    status='completed',
                    reference=f"TRF-{request.user.id}-{int(__import__('time').time())}"
                )
            
            messages.success(request, f"Successfully transferred ${amount} to your main balance.")
        except Exception as e:
            messages.error(request, f"Transfer failed: {str(e)}")
    
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
def sell_asset(request, investment_id):
    """Sell an asset investment and credit trading balance."""
    investment = get_object_or_404(Investment, id=investment_id, user=request.user)
    
    if investment.status != 'active':
        messages.error(request, "This investment is no longer active.")
        return redirect('shares')
    
    if not investment.asset:
        messages.error(request, "This is not a share/bond investment.")
        return redirect('shares')
    
    if request.method == 'POST':
        from decimal import Decimal
        import time
        
        # Calculate current value
        current_value = investment.units * investment.asset.current_price
        profit = current_value - investment.amount_invested
        
        with transaction.atomic():
            account = request.user.account
            
            # Credit trading balance with current value
            account.trading_balance += current_value
            account.save()
            
            # Mark investment as sold
            investment.status = 'sold'
            investment.save()
            
            # Create transaction record
            Transaction.objects.create(
                account=account,
                transaction_type='deposit',
                amount=current_value,
                description=f"Sold {investment.asset.name} ({investment.units:.4f} units)",
                status='completed',
                reference=f"SELL-{investment.asset.id}-{request.user.id}-{int(time.time())}"
            )
        
        # Determine if profit or loss
        if profit >= 0:
            messages.success(request, f"Sold {investment.asset.name} for ${current_value:.2f} (+${profit:.2f} profit). Funds added to your Trading Wallet.")
        else:
            messages.success(request, f"Sold {investment.asset.name} for ${current_value:.2f} (${profit:.2f} loss). Funds added to your Trading Wallet.")
        
        # Send email notification
        try:
            send_investment_email(
                user=request.user,
                investment_type='share',
                investment_name=f"Sold: {investment.asset.name}",
                amount=current_value,
                units=investment.units,
                price=investment.asset.current_price
            )
        except:
            pass
        
        return redirect('shares')
    
    # GET request - show confirmation page (or just redirect back)
    return redirect('shares')


# Notification API Views
def get_notifications(request):
    """Return user's notifications as JSON."""
    if not request.user.is_authenticated:
        return JsonResponse({'unread_count': 0, 'notifications': []})
    
    notifications = Notification.objects.filter(user=request.user)[:20]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%b %d, %Y %I:%M %p'),
            }
            for n in notifications
        ]
    }
    return JsonResponse(data)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read."""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def mark_all_notifications_read(request):
    """Mark all user notifications as read."""
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
