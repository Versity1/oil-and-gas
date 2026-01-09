from django.contrib import admin
from .models import Account, Transaction, PaymentMethod, Deposit, Withdrawal

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
    list_display = ('user', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('user__username', 'transaction_hash')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'network', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'wallet_address')
    readonly_fields = ('created_at', 'updated_at')
