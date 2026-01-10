from django.contrib import admin
from .models import Account, Transaction, PaymentMethod, Deposit, Withdrawal, Project, Asset, Investment, InvestmentPlan, UserPlan

@admin.register(InvestmentPlan)
class InvestmentPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'daily_profit_rate', 'min_price', 'max_price', 'duration_days', 'is_active')
    list_filter = ('is_active', 'capital_return')
    search_fields = ('name',)

@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'amount', 'current_profit', 'is_active', 'start_date')
    list_filter = ('is_active', 'plan')
    search_fields = ('user__username', 'plan__name')
    readonly_fields = ('start_date', 'last_profit_at')

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_number', 'balance', 'updated_at')
    search_fields = ('user__username', 'account_number')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'account', 'transaction_type', 'amount', 'status', 'timestamp')
    list_filter = ('transaction_type', 'status')
    search_fields = ('reference', 'account__user__username')

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'network', 'is_active')
    list_filter = ('is_active',)

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'payment_method', 'status', 'linked_plan', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('user__username', 'transaction_hash')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'wallet_name', 'network', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'wallet_address', 'wallet_name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'min_investment', 'return_rate', 'duration_days', 'status')
    list_filter = ('status',)
    search_fields = ('title',)

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'ticker', 'asset_type', 'current_price', 'is_active')
    list_filter = ('asset_type', 'is_active')
    search_fields = ('name', 'ticker')

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_target', 'amount_invested', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'project__title', 'asset__name')

    def get_target(self, obj):
        return obj.project.title if obj.project else obj.asset.name
    get_target.short_description = 'Target'
