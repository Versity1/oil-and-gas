from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    Account, Deposit, Withdrawal, Transaction, 
    InvestmentPlan, UserPlan, Project, Asset, 
    Investment, PaymentMethod
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
        'recent_deposits': recent_deposits,
        'recent_withdrawals': recent_withdrawals,
        'recent_users': recent_users,
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
        deposit.status = 'completed'
        deposit.save()
        
        # Credit user's account
        account = deposit.user.account
        account.balance += deposit.amount
        account.save()
        
        # Create transaction record
        Transaction.objects.create(
            account=account,
            transaction_type='deposit',
            amount=deposit.amount,
            description=f"Deposit via {deposit.payment_method.name}",
            status='completed'
        )
        
        # If linked to a plan, create UserPlan
        if deposit.linked_plan:
            UserPlan.objects.create(
                user=deposit.user,
                plan=deposit.linked_plan,
                amount=deposit.amount
            )
            # Deduct from balance for the plan
            account.balance -= deposit.amount
            account.save()
        
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
        withdrawal.status = 'completed'
        withdrawal.save()
        
        # Create transaction record (balance already deducted on request)
        Transaction.objects.create(
            account=withdrawal.user.account,
            transaction_type='withdrawal',
            amount=withdrawal.amount,
            description=f"Withdrawal to {withdrawal.network} wallet",
            status='completed'
        )
        
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
def admin_projects(request):
    """Projects management."""
    projects = Project.objects.all().order_by('-created_at')
    
    context = {
        'projects': projects,
    }
    return render(request, 'custom_admin/projects.html', context)


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
