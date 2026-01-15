from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from decimal import Decimal

from .models import (
    Account, Deposit, Withdrawal, Transaction, 
    InvestmentPlan, UserPlan, Project, Asset, 
    Investment, PaymentMethod, Notification, KYCDocument
)


@staff_member_required
def admin_dashboard(request):
    """Admin dashboard with overview stats."""
    # Get counts
    total_users = User.objects.count()
    pending_deposits = Deposit.objects.filter(status='pending').count()
    pending_withdrawals = Withdrawal.objects.filter(status='pending').count()
    active_plans = UserPlan.objects.filter(is_active=True).count()
    
    # Get totals
    total_deposits = Deposit.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_withdrawals = Withdrawal.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_balance = Account.objects.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
    total_trading_balance = Account.objects.aggregate(total=Sum('trading_balance'))['total'] or Decimal('0.00')
    
    # Shares & Bonds Metrics
    total_assets = Asset.objects.count()
    active_assets = Asset.objects.filter(is_active=True).count()
    total_shares = Asset.objects.filter(asset_type='share').count()
    total_bonds = Asset.objects.filter(asset_type='bond').count()
    
    # Asset Investments
    total_asset_investments = Investment.objects.filter(asset__isnull=False, status='active').count()
    total_asset_invested = Investment.objects.filter(asset__isnull=False, status='active').aggregate(total=Sum('amount_invested'))['total'] or Decimal('0.00')
    
    # Calculate total current value of all asset investments
    active_asset_investments = Investment.objects.filter(asset__isnull=False, status='active').select_related('asset')
    total_current_value = sum(
        inv.units * inv.asset.current_price for inv in active_asset_investments
    ) if active_asset_investments else Decimal('0.00')
    
    # Unrealized P&L
    unrealized_pnl = total_current_value - total_asset_invested
    
    # Top performing assets (by number of investors)
    top_assets = Asset.objects.filter(is_active=True).annotate(
        investor_count=Count('investment', filter=Q(investment__status='active')),
        total_invested=Sum('investment__amount_invested', filter=Q(investment__status='active'))
    ).order_by('-investor_count')[:5]
    
    # Recent asset trades (sold investments)
    recent_trades = Investment.objects.filter(
        asset__isnull=False, 
        status='sold'
    ).select_related('user', 'asset').order_by('-created_at')[:5]
    
    # Recent activity
    recent_deposits = Deposit.objects.select_related('user', 'payment_method').order_by('-created_at')[:5]
    recent_withdrawals = Withdrawal.objects.select_related('user').order_by('-created_at')[:5]
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    context = {
        'total_users': total_users,
        'pending_deposits': pending_deposits,
        'pending_withdrawals': pending_withdrawals,
        'active_plans': active_plans,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_balance': total_balance,
        'total_trading_balance': total_trading_balance,
        'recent_deposits': recent_deposits,
        'recent_withdrawals': recent_withdrawals,
        'recent_users': recent_users,
        # Shares & Bonds metrics
        'total_assets': total_assets,
        'active_assets': active_assets,
        'total_shares': total_shares,
        'total_bonds': total_bonds,
        'total_asset_investments': total_asset_investments,
        'total_asset_invested': total_asset_invested,
        'total_current_value': total_current_value,
        'unrealized_pnl': unrealized_pnl,
        'top_assets': top_assets,
        'recent_trades': recent_trades,
    }
    return render(request, 'custom_admin/dashboard.html', context)


@staff_member_required
def admin_users(request):
    """User management view."""
    search = request.GET.get('search', '')
    users = User.objects.select_related('account').order_by('-date_joined')
    
    if search:
        users = users.filter(
            Q(username__icontains=search) | 
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    context = {
        'users': users,
        'search': search,
    }
    return render(request, 'custom_admin/users.html', context)


@staff_member_required
def admin_deposits(request):
    """Deposit management with approve/reject."""
    status_filter = request.GET.get('status', 'all')
    deposits = Deposit.objects.select_related('user', 'payment_method', 'linked_plan').order_by('-created_at')
    
    if status_filter != 'all':
        deposits = deposits.filter(status=status_filter)
    
    context = {
        'deposits': deposits,
        'status_filter': status_filter,
    }
    return render(request, 'custom_admin/deposits.html', context)


@staff_member_required
def admin_approve_deposit(request, deposit_id):
    """Approve a pending deposit."""
    deposit = get_object_or_404(Deposit, id=deposit_id)
    
    if deposit.status == 'pending':
        # Simply change status to completed
        # The signal handler (handle_deposit_update in signals.py) will:
        # - Credit the user's account balance
        # - Create the transaction record
        # - Handle linked investments (project/asset/plan)
        deposit.status = 'completed'
        deposit.save()
        
        messages.success(request, f"Deposit of ${deposit.amount} approved successfully.")
    else:
        messages.warning(request, "This deposit has already been processed.")
    
    return redirect('admin_deposits')


@staff_member_required
def admin_reject_deposit(request, deposit_id):
    """Reject a pending deposit."""
    deposit = get_object_or_404(Deposit, id=deposit_id)
    
    if deposit.status == 'pending':
        deposit.status = 'failed'
        deposit.save()
        messages.success(request, f"Deposit of ${deposit.amount} rejected.")
    else:
        messages.warning(request, "This deposit has already been processed.")
    
    return redirect('admin_deposits')


@staff_member_required
def admin_withdrawals(request):
    """Withdrawal management with approve/reject."""
    status_filter = request.GET.get('status', 'all')
    withdrawals = Withdrawal.objects.select_related('user').order_by('-created_at')
    
    if status_filter != 'all':
        withdrawals = withdrawals.filter(status=status_filter)
    
    context = {
        'withdrawals': withdrawals,
        'status_filter': status_filter,
    }
    return render(request, 'custom_admin/withdrawals.html', context)


@staff_member_required
def admin_approve_withdrawal(request, withdrawal_id):
    """Approve a pending withdrawal."""
    withdrawal = get_object_or_404(Withdrawal, id=withdrawal_id)
    
    if withdrawal.status == 'pending':
        # Simply change status to completed
        # The signal handler (handle_withdrawal_update in signals.py) will:
        # - Deduct from user's account balance
        # - Create the transaction record
        withdrawal.status = 'completed'
        withdrawal.save()
        
        messages.success(request, f"Withdrawal of ${withdrawal.amount} approved successfully.")
    else:
        messages.warning(request, "This withdrawal has already been processed.")
    
    return redirect('admin_withdrawals')


@staff_member_required
def admin_reject_withdrawal(request, withdrawal_id):
    """Reject a pending withdrawal and refund the user."""
    withdrawal = get_object_or_404(Withdrawal, id=withdrawal_id)
    
    if withdrawal.status == 'pending':
        withdrawal.status = 'failed'
        withdrawal.save()
        
        # Refund the user
        account = withdrawal.user.account
        account.balance += withdrawal.amount
        account.save()
        
        messages.success(request, f"Withdrawal of ${withdrawal.amount} rejected. Amount refunded to user.")
    else:
        messages.warning(request, "This withdrawal has already been processed.")
    
    return redirect('admin_withdrawals')


@staff_member_required
def admin_transactions(request):
    """View all transactions."""
    type_filter = request.GET.get('type', 'all')
    transactions = Transaction.objects.select_related('account__user').order_by('-timestamp')
    
    if type_filter != 'all':
        transactions = transactions.filter(transaction_type=type_filter)
    
    context = {
        'transactions': transactions,
        'type_filter': type_filter,
    }
    return render(request, 'custom_admin/transactions.html', context)


@staff_member_required
def admin_investment_plans(request):
    """Investment plans management."""
    plans = InvestmentPlan.objects.all().order_by('-created_at')
    
    context = {
        'plans': plans,
    }
    return render(request, 'custom_admin/investment_plans.html', context)


@staff_member_required
def admin_toggle_plan(request, plan_id):
    """Toggle investment plan active status."""
    plan = get_object_or_404(InvestmentPlan, id=plan_id)
    plan.is_active = not plan.is_active
    plan.save()
    
    status = "activated" if plan.is_active else "deactivated"
    messages.success(request, f"Plan '{plan.name}' has been {status}.")
    return redirect('admin_investment_plans')


@staff_member_required
def admin_create_plan(request):
    """Create a new investment plan."""
    if request.method == 'POST':
        name = request.POST.get('name')
        short_description = request.POST.get('short_description')
        min_price = request.POST.get('min_price')
        max_price = request.POST.get('max_price')
        daily_profit_rate = request.POST.get('daily_profit_rate')
        duration_days = request.POST.get('duration_days')
        capital_return = request.POST.get('capital_return') == 'on'
        
        try:
            min_price = Decimal(min_price)
            max_price = Decimal(max_price)
            daily_profit_rate = Decimal(daily_profit_rate)
            duration_days = int(duration_days)
            
            if min_price <= 0 or max_price <= 0 or daily_profit_rate <= 0:
                raise ValueError("Values must be positive")
            if min_price > max_price:
                raise ValueError("Min price cannot exceed max price")
        except Exception as e:
            messages.error(request, f"Invalid data: {e}")
            return redirect('admin_investment_plans')
        
        InvestmentPlan.objects.create(
            name=name,
            short_description=short_description,
            min_price=min_price,
            max_price=max_price,
            daily_profit_rate=daily_profit_rate,
            duration_days=duration_days,
            capital_return=capital_return,
            is_active=True
        )
        
        messages.success(request, f"Investment plan '{name}' created successfully.")
    
    return redirect('admin_investment_plans')


@staff_member_required
def admin_edit_plan(request, plan_id):
    """Edit an investment plan."""
    plan = get_object_or_404(InvestmentPlan, id=plan_id)
    
    if request.method == 'POST':
        plan.name = request.POST.get('name', plan.name)
        plan.short_description = request.POST.get('short_description', plan.short_description)
        
        try:
            plan.min_price = Decimal(request.POST.get('min_price', plan.min_price))
            plan.max_price = Decimal(request.POST.get('max_price', plan.max_price))
            plan.daily_profit_rate = Decimal(request.POST.get('daily_profit_rate', plan.daily_profit_rate))
            plan.duration_days = int(request.POST.get('duration_days', plan.duration_days))
        except:
            messages.error(request, "Invalid numeric data provided.")
            return redirect('admin_investment_plans')
        
        plan.capital_return = request.POST.get('capital_return') == 'on'
        plan.save()
        
        messages.success(request, f"Plan '{plan.name}' updated successfully.")
    
    return redirect('admin_investment_plans')


@staff_member_required
def admin_delete_plan(request, plan_id):
    """Delete an investment plan."""
    plan = get_object_or_404(InvestmentPlan, id=plan_id)
    
    if request.method == 'POST':
        name = plan.name
        # Check for active user subscriptions
        active_subs = UserPlan.objects.filter(plan=plan, is_active=True).count()
        
        if active_subs > 0:
            messages.error(request, f"Cannot delete '{name}' - there are {active_subs} active subscribers.")
            return redirect('admin_investment_plans')
        
        plan.delete()
        messages.success(request, f"Plan '{name}' deleted successfully.")
    
    return redirect('admin_investment_plans')


@staff_member_required
def admin_projects(request):
    """Projects management."""
    projects = Project.objects.all().order_by('-created_at')
    
    context = {
        'projects': projects,
    }
    return render(request, 'custom_admin/projects.html', context)


@staff_member_required
def admin_create_project(request):
    """Create a new project."""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        min_investment = request.POST.get('min_investment')
        return_rate = request.POST.get('return_rate')
        duration_days = request.POST.get('duration_days')
        status = request.POST.get('status', 'funding')
        image = request.FILES.get('image')
        
        try:
            min_investment = Decimal(min_investment)
            return_rate = Decimal(return_rate)
            duration_days = int(duration_days)
            
            if min_investment <= 0 or return_rate <= 0:
                raise ValueError("Values must be positive")
        except Exception as e:
            messages.error(request, f"Invalid data: {e}")
            return redirect('admin_projects')
        
        Project.objects.create(
            title=title,
            description=description,
            min_investment=min_investment,
            return_rate=return_rate,
            duration_days=duration_days,
            status=status,
            image=image
        )
        
        messages.success(request, f"Project '{title}' created successfully.")
    
    return redirect('admin_projects')


@staff_member_required
def admin_edit_project(request, project_id):
    """Edit a project."""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        project.title = request.POST.get('title', project.title)
        project.description = request.POST.get('description', project.description)
        project.status = request.POST.get('status', project.status)
        
        try:
            project.min_investment = Decimal(request.POST.get('min_investment', project.min_investment))
            project.return_rate = Decimal(request.POST.get('return_rate', project.return_rate))
            project.duration_days = int(request.POST.get('duration_days', project.duration_days))
        except:
            messages.error(request, "Invalid numeric data provided.")
            return redirect('admin_projects')
        
        if 'image' in request.FILES:
            project.image = request.FILES['image']
        
        project.save()
        messages.success(request, f"Project '{project.title}' updated successfully.")
    
    return redirect('admin_projects')


@staff_member_required
def admin_delete_project(request, project_id):
    """Delete a project."""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        title = project.title
        # Check for active investments
        active_investments = Investment.objects.filter(project=project, status='active').count()
        
        if active_investments > 0:
            messages.error(request, f"Cannot delete '{title}' - there are {active_investments} active investments.")
            return redirect('admin_projects')
        
        project.delete()
        messages.success(request, f"Project '{title}' deleted successfully.")
    
    return redirect('admin_projects')


@staff_member_required
def admin_assets(request):
    """Assets (shares/bonds) management."""
    assets = Asset.objects.all().order_by('name')
    
    context = {
        'assets': assets,
    }
    return render(request, 'custom_admin/assets.html', context)


@staff_member_required
def admin_toggle_asset(request, asset_id):
    """Toggle asset active status."""
    asset = get_object_or_404(Asset, id=asset_id)
    asset.is_active = not asset.is_active
    asset.save()
    
    status = "activated" if asset.is_active else "deactivated"
    messages.success(request, f"Asset '{asset.name}' has been {status}.")
    return redirect('admin_assets')


@staff_member_required
def admin_payment_methods(request):
    """Payment methods management."""
    methods = PaymentMethod.objects.all().order_by('name')
    
    context = {
        'methods': methods,
    }
    return render(request, 'custom_admin/payment_methods.html', context)


@staff_member_required
def admin_toggle_payment_method(request, method_id):
    """Toggle payment method active status."""
    method = get_object_or_404(PaymentMethod, id=method_id)
    method.is_active = not method.is_active
    method.save()
    
    status = "activated" if method.is_active else "deactivated"
    messages.success(request, f"Payment method '{method.name}' has been {status}.")
    return redirect('admin_payment_methods')


@staff_member_required
def admin_create_payment_method(request):
    """Create a new payment method."""
    if request.method == 'POST':
        name = request.POST.get('name')
        symbol = request.POST.get('symbol', '').upper()
        network = request.POST.get('network')
        wallet_address = request.POST.get('wallet_address')
        qr_code = request.FILES.get('qr_code')
        thumbnail = request.FILES.get('thumbnail')
        
        if not all([name, symbol, network, wallet_address]):
            messages.error(request, "All required fields must be filled.")
            return redirect('admin_payment_methods')
        
        PaymentMethod.objects.create(
            name=name,
            symbol=symbol,
            network=network,
            wallet_address=wallet_address,
            qr_code=qr_code,
            thumbnail=thumbnail,
            is_active=True
        )
        
        messages.success(request, f"Payment method '{name}' created successfully.")
    
    return redirect('admin_payment_methods')


@staff_member_required
def admin_edit_payment_method(request, method_id):
    """Edit a payment method."""
    method = get_object_or_404(PaymentMethod, id=method_id)
    
    if request.method == 'POST':
        method.name = request.POST.get('name', method.name)
        method.symbol = request.POST.get('symbol', method.symbol).upper()
        method.network = request.POST.get('network', method.network)
        method.wallet_address = request.POST.get('wallet_address', method.wallet_address)
        
        if 'qr_code' in request.FILES:
            method.qr_code = request.FILES['qr_code']
        if 'thumbnail' in request.FILES:
            method.thumbnail = request.FILES['thumbnail']
        
        method.save()
        messages.success(request, f"Payment method '{method.name}' updated successfully.")
    
    return redirect('admin_payment_methods')


@staff_member_required
def admin_delete_payment_method(request, method_id):
    """Delete a payment method."""
    method = get_object_or_404(PaymentMethod, id=method_id)
    
    if request.method == 'POST':
        name = method.name
        # Check for pending deposits using this method
        pending_deposits = Deposit.objects.filter(payment_method=method, status='pending').count()
        
        if pending_deposits > 0:
            messages.error(request, f"Cannot delete '{name}' - there are {pending_deposits} pending deposits using this method.")
            return redirect('admin_payment_methods')
        
        method.delete()
        messages.success(request, f"Payment method '{name}' deleted successfully.")
    
    return redirect('admin_payment_methods')


@staff_member_required
def admin_user_plans(request):
    """View all user investment plans."""
    status_filter = request.GET.get('status', 'all')
    user_plans = UserPlan.objects.select_related('user', 'plan').order_by('-start_date')
    
    if status_filter == 'active':
        user_plans = user_plans.filter(is_active=True)
    elif status_filter == 'inactive':
        user_plans = user_plans.filter(is_active=False)
    
    context = {
        'user_plans': user_plans,
        'status_filter': status_filter,
    }
    return render(request, 'custom_admin/user_plans.html', context)


# ========== USER MANAGEMENT ACTIONS ==========

@staff_member_required
def admin_user_detail(request, user_id):
    """View detailed user information."""
    user_obj = get_object_or_404(User, id=user_id)
    
    # Get user's data
    deposits = Deposit.objects.filter(user=user_obj).order_by('-created_at')[:10]
    withdrawals = Withdrawal.objects.filter(user=user_obj).order_by('-created_at')[:10]
    transactions = Transaction.objects.filter(account=user_obj.account).order_by('-timestamp')[:10]
    user_plans = UserPlan.objects.filter(user=user_obj).select_related('plan')
    investments = Investment.objects.filter(user=user_obj).select_related('project', 'asset')
    
    # Stats
    total_deposited = Deposit.objects.filter(user=user_obj, status='completed').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_withdrawn = Withdrawal.objects.filter(user=user_obj, status='completed').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'user_obj': user_obj,
        'deposits': deposits,
        'withdrawals': withdrawals,
        'transactions': transactions,
        'user_plans': user_plans,
        'investments': investments,
        'total_deposited': total_deposited,
        'total_withdrawn': total_withdrawn,
    }
    return render(request, 'custom_admin/user_detail.html', context)


@staff_member_required
def admin_toggle_user(request, user_id):
    """Suspend or activate a user."""
    user_obj = get_object_or_404(User, id=user_id)
    
    # Don't allow suspending yourself or superusers
    if user_obj == request.user:
        messages.error(request, "You cannot suspend yourself.")
        return redirect('admin_users')
    
    if user_obj.is_superuser:
        messages.error(request, "You cannot suspend a superuser.")
        return redirect('admin_users')
    
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    
    status = "activated" if user_obj.is_active else "suspended"
    messages.success(request, f"User '{user_obj.username}' has been {status}.")
    return redirect('admin_users')


@staff_member_required
def admin_delete_user(request, user_id):
    """Delete a user account."""
    user_obj = get_object_or_404(User, id=user_id)
    
    # Safety checks
    if user_obj == request.user:
        messages.error(request, "You cannot delete yourself.")
        return redirect('admin_users')
    
    if user_obj.is_superuser:
        messages.error(request, "You cannot delete a superuser.")
        return redirect('admin_users')
    
    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f"User '{username}' has been permanently deleted.")
        return redirect('admin_users')
    
    # GET request - show confirmation
    context = {'user_obj': user_obj}
    return render(request, 'custom_admin/confirm_delete.html', context)


@staff_member_required
def admin_adjust_balance(request, user_id):
    """Credit or debit a user's balance."""
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        amount = request.POST.get('amount')
        reason = request.POST.get('reason', '')
        
        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except:
            messages.error(request, "Invalid amount provided.")
            return redirect('admin_user_detail', user_id=user_id)
        
        account = user_obj.account
        
        if action == 'credit':
            account.balance += amount
            account.save()
            
            Transaction.objects.create(
                account=account,
                transaction_type='deposit',
                amount=amount,
                description=f"Admin credit: {reason}" if reason else "Admin credit adjustment",
                status='completed'
            )
            messages.success(request, f"Credited ${amount} to {user_obj.username}'s account.")
            
        elif action == 'debit':
            if account.balance < amount:
                messages.error(request, f"Insufficient balance. User has ${account.balance}.")
                return redirect('admin_user_detail', user_id=user_id)
            
            account.balance -= amount
            account.save()
            
            Transaction.objects.create(
                account=account,
                transaction_type='withdrawal',
                amount=amount,
                description=f"Admin debit: {reason}" if reason else "Admin debit adjustment",
                status='completed'
            )
            messages.success(request, f"Debited ${amount} from {user_obj.username}'s account.")
    
    return redirect('admin_user_detail', user_id=user_id)


# ========== ASSET PRICE UPDATE ==========

@staff_member_required
def admin_update_asset_price(request, asset_id):
    """Update asset price."""
    asset = get_object_or_404(Asset, id=asset_id)
    
    if request.method == 'POST':
        new_price = request.POST.get('price')
        
        try:
            new_price = Decimal(new_price)
            if new_price <= 0:
                raise ValueError("Price must be positive")
        except:
            messages.error(request, "Invalid price provided.")
            return redirect('admin_assets')
        
        # Store old price
        asset.previous_price = asset.current_price
        asset.current_price = new_price
        asset.save()
        
        messages.success(request, f"Updated {asset.name} price to ${new_price}.")
    
    return redirect('admin_assets')


@staff_member_required
def admin_create_asset(request):
    """Create a new asset/share."""
    if request.method == 'POST':
        name = request.POST.get('name')
        ticker = request.POST.get('ticker', '').upper()
        asset_type = request.POST.get('asset_type', 'share')
        current_price = request.POST.get('current_price')
        interest_rate = request.POST.get('interest_rate')
        maturity_date = request.POST.get('maturity_date')
        
        try:
            current_price = Decimal(current_price)
            if current_price <= 0:
                raise ValueError("Price must be positive")
        except:
            messages.error(request, "Invalid price provided.")
            return redirect('admin_assets')
        
        # Check for duplicate ticker
        if Asset.objects.filter(ticker=ticker).exists():
            messages.error(request, f"Asset with ticker '{ticker}' already exists.")
            return redirect('admin_assets')
        
        asset = Asset.objects.create(
            name=name,
            ticker=ticker,
            asset_type=asset_type,
            current_price=current_price,
            previous_price=current_price,
            interest_rate=Decimal(interest_rate) if interest_rate else None,
            maturity_date=maturity_date if maturity_date else None,
            is_active=True
        )
        
        messages.success(request, f"Asset '{name}' created successfully.")
    
    return redirect('admin_assets')


@staff_member_required
def admin_edit_asset(request, asset_id):
    """Edit an existing asset."""
    asset = get_object_or_404(Asset, id=asset_id)
    
    if request.method == 'POST':
        asset.name = request.POST.get('name', asset.name)
        new_ticker = request.POST.get('ticker', asset.ticker).upper()
        
        # Check if new ticker conflicts with another asset
        if new_ticker != asset.ticker and Asset.objects.filter(ticker=new_ticker).exists():
            messages.error(request, f"Asset with ticker '{new_ticker}' already exists.")
            return redirect('admin_assets')
        
        asset.ticker = new_ticker
        asset.asset_type = request.POST.get('asset_type', asset.asset_type)
        
        new_price = request.POST.get('current_price')
        if new_price:
            try:
                new_price = Decimal(new_price)
                if new_price != asset.current_price:
                    asset.previous_price = asset.current_price
                    asset.current_price = new_price
            except:
                pass
        
        interest_rate = request.POST.get('interest_rate')
        asset.interest_rate = Decimal(interest_rate) if interest_rate else None
        
        maturity_date = request.POST.get('maturity_date')
        asset.maturity_date = maturity_date if maturity_date else None
        
        asset.save()
        messages.success(request, f"Asset '{asset.name}' updated successfully.")
    
    return redirect('admin_assets')


@staff_member_required
def admin_delete_asset(request, asset_id):
    """Delete an asset."""
    asset = get_object_or_404(Asset, id=asset_id)
    
    if request.method == 'POST':
        name = asset.name
        # Check if there are active investments
        active_investments = Investment.objects.filter(asset=asset, status='active').count()
        
        if active_investments > 0:
            messages.error(request, f"Cannot delete '{name}' - there are {active_investments} active investments.")
            return redirect('admin_assets')
        
        asset.delete()
        messages.success(request, f"Asset '{name}' deleted successfully.")
    
    return redirect('admin_assets')


# ========== PROJECT STATUS UPDATE ==========

@staff_member_required 
def admin_update_project_status(request, project_id):
    """Update project status."""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status in ['funding', 'active', 'completed']:
            project.status = new_status
            project.save()
            messages.success(request, f"Project '{project.title}' status updated to {new_status}.")
        else:
            messages.error(request, "Invalid status provided.")
    
    return redirect('admin_projects')


# ========== USER PLAN MANAGEMENT ==========

@staff_member_required
def admin_toggle_user_plan(request, plan_id):
    """Toggle user plan active status or mark as completed."""
    user_plan = get_object_or_404(UserPlan, id=plan_id)
    user_plan.is_active = not user_plan.is_active
    user_plan.save()
    
    status = "activated" if user_plan.is_active else "completed/deactivated"
    messages.success(request, f"User plan has been {status}.")
    return redirect('admin_user_plans')


@staff_member_required
def admin_add_profit(request, plan_id):
    """Manually add profit to a user plan."""
    user_plan = get_object_or_404(UserPlan, id=plan_id)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        
        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except:
            messages.error(request, "Invalid amount provided.")
            return redirect('admin_user_plans')
        
        # Add to profit
        user_plan.current_profit += amount
        user_plan.save()
        
        # Credit user's account
        account = user_plan.user.account
        account.balance += amount
        account.save()
        
        # Create transaction
        Transaction.objects.create(
            account=account,
            transaction_type='profit',
            amount=amount,
            description=f"Profit from {user_plan.plan.name}",
            status='completed'
        )
        
        messages.success(request, f"Added ${amount} profit to {user_plan.user.username}'s plan.")
    
    return redirect('admin_user_plans')


# ========== NOTIFICATION MANAGEMENT ==========

@staff_member_required
def admin_notifications(request):
    """List all notifications with filtering and send notification form."""
    user_filter = request.GET.get('user', '')
    type_filter = request.GET.get('type', 'all')
    
    notifications = Notification.objects.select_related('user').order_by('-created_at')
    
    if user_filter:
        notifications = notifications.filter(
            Q(user__username__icontains=user_filter) |
            Q(user__email__icontains=user_filter)
        )
    
    if type_filter != 'all':
        notifications = notifications.filter(notification_type=type_filter)
    
    # Get all users for the send notification form
    users = User.objects.filter(is_active=True).order_by('username')
    
    context = {
        'notifications': notifications[:100],  # Limit to recent 100
        'users': users,
        'user_filter': user_filter,
        'type_filter': type_filter,
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    return render(request, 'custom_admin/notifications.html', context)


@staff_member_required
def admin_send_notification(request):
    """Send a notification to one or all users."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        notification_type = request.POST.get('notification_type', 'info')
        target = request.POST.get('target', 'single')
        user_id = request.POST.get('user_id')
        
        if not title or not message:
            messages.error(request, "Title and message are required.")
            return redirect('admin_notifications')
        
        if target == 'all':
            # Send to all active users
            users = User.objects.filter(is_active=True)
            notifications_created = 0
            for user in users:
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    notification_type=notification_type
                )
                notifications_created += 1
            messages.success(request, f"Notification sent to {notifications_created} users.")
        else:
            # Send to single user
            if not user_id:
                messages.error(request, "Please select a user.")
                return redirect('admin_notifications')
            
            user = get_object_or_404(User, id=user_id)
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            messages.success(request, f"Notification sent to {user.username}.")
    
    return redirect('admin_notifications')


@staff_member_required
def admin_delete_notification(request, notification_id):
    """Delete a notification."""
    notification = get_object_or_404(Notification, id=notification_id)
    
    if request.method == 'POST':
        notification.delete()
        messages.success(request, "Notification deleted.")
    
    return redirect('admin_notifications')


@staff_member_required
def admin_pending_counts(request):
    """Return pending deposits/withdrawals count as JSON for header badge."""
    pending_deposits = Deposit.objects.filter(status='pending').count()
    pending_withdrawals = Withdrawal.objects.filter(status='pending').count()
    
    return JsonResponse({
        'pending_deposits': pending_deposits,
        'pending_withdrawals': pending_withdrawals,
        'total_pending': pending_deposits + pending_withdrawals,
    })


# ========== KYC MANAGEMENT ==========

@staff_member_required
def admin_kyc_list(request):
    """List all KYC submissions with filtering."""
    status_filter = request.GET.get('status', 'all')
    kyc_documents = KYCDocument.objects.select_related('user').order_by('-submitted_at')
    
    if status_filter != 'all':
        kyc_documents = kyc_documents.filter(status=status_filter)
    
    # Count by status for quick stats
    pending_count = KYCDocument.objects.filter(status='pending').count()
    approved_count = KYCDocument.objects.filter(status='approved').count()
    rejected_count = KYCDocument.objects.filter(status='rejected').count()
    
    context = {
        'kyc_documents': kyc_documents,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'custom_admin/kyc.html', context)


@staff_member_required
def admin_kyc_approve(request, kyc_id):
    """Approve a KYC submission."""
    kyc = get_object_or_404(KYCDocument, id=kyc_id)
    
    if request.method == 'POST':
        kyc.status = 'approved'
        kyc.rejection_reason = ''
        kyc.reviewed_at = timezone.now()
        kyc.save()
        
        # Create notification for user
        Notification.objects.create(
            user=kyc.user,
            title="KYC Approved",
            message="Your identity verification has been approved. You can now make withdrawals.",
            notification_type="success"
        )
        
        messages.success(request, f"KYC for {kyc.user.username} has been approved.")
    
    return redirect('admin_kyc_list')


@staff_member_required
def admin_kyc_reject(request, kyc_id):
    """Reject a KYC submission with reason."""
    kyc = get_object_or_404(KYCDocument, id=kyc_id)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            messages.error(request, "Please provide a rejection reason.")
            return redirect('admin_kyc_list')
        
        kyc.status = 'rejected'
        kyc.rejection_reason = rejection_reason
        kyc.reviewed_at = timezone.now()
        kyc.save()
        
        # Create notification for user
        Notification.objects.create(
            user=kyc.user,
            title="KYC Rejected",
            message=f"Your identity verification was rejected. Reason: {rejection_reason}",
            notification_type="warning"
        )
        
        messages.success(request, f"KYC for {kyc.user.username} has been rejected.")
    
    return redirect('admin_kyc_list')
