from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import admin_views

urlpatterns = [
    # Front Pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),
    path('products/', views.products, name='products'),
    
    # Auth Pages
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='password_reset.html'), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), 
         name='password_reset_complete'),
    
    # Dashboard Pages
    path('dashboard/', views.dashboard, name='dashboard'),
    path('investment-plan/', views.investment_plan, name='investment_plan'),
    path('investment-packages/', views.investment_packages, name='investment_packages'),
    path('shares/', views.shares, name='shares'),
    path('transaction-history/', views.transaction_history, name='transaction_history'),
    path('deposit/', views.deposit, name='deposit'),
    path('withdrawal/', views.withdrawal, name='withdrawal'),
    path('buy-project/<int:project_id>/', views.buy_project, name='buy_project'),
    path('buy-asset/<int:asset_id>/', views.buy_asset, name='buy_asset'),
    path('buy-package/<int:package_id>/', views.buy_package, name='buy_package'),
    path('deposit/<int:deposit_id>/pay/', views.deposit_pay, name='deposit_pay'),
    path('transfer-to-main/', views.transfer_to_main, name='transfer_to_main'),
    path('sell-asset/<int:investment_id>/', views.sell_asset, name='sell_asset'),
    path('referrals/', views.referral_dashboard, name='referral_dashboard'),
    
    # Notification API
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # Custom Admin Pages
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', admin_views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/', admin_views.admin_user_detail, name='admin_user_detail'),
    path('admin/users/<int:user_id>/toggle/', admin_views.admin_toggle_user, name='admin_toggle_user'),
    path('admin/users/<int:user_id>/delete/', admin_views.admin_delete_user, name='admin_delete_user'),
    path('admin/users/<int:user_id>/adjust-balance/', admin_views.admin_adjust_balance, name='admin_adjust_balance'),
    path('admin/deposits/', admin_views.admin_deposits, name='admin_deposits'),
    path('admin/deposits/<int:deposit_id>/approve/', admin_views.admin_approve_deposit, name='admin_approve_deposit'),
    path('admin/deposits/<int:deposit_id>/reject/', admin_views.admin_reject_deposit, name='admin_reject_deposit'),
    path('admin/withdrawals/', admin_views.admin_withdrawals, name='admin_withdrawals'),
    path('admin/withdrawals/<int:withdrawal_id>/approve/', admin_views.admin_approve_withdrawal, name='admin_approve_withdrawal'),
    path('admin/withdrawals/<int:withdrawal_id>/reject/', admin_views.admin_reject_withdrawal, name='admin_reject_withdrawal'),
    path('admin/transactions/', admin_views.admin_transactions, name='admin_transactions'),
    path('admin/investment-plans/', admin_views.admin_investment_plans, name='admin_investment_plans'),
    path('admin/investment-plans/create/', admin_views.admin_create_plan, name='admin_create_plan'),
    path('admin/investment-plans/<int:plan_id>/toggle/', admin_views.admin_toggle_plan, name='admin_toggle_plan'),
    path('admin/investment-plans/<int:plan_id>/edit/', admin_views.admin_edit_plan, name='admin_edit_plan'),
    path('admin/investment-plans/<int:plan_id>/delete/', admin_views.admin_delete_plan, name='admin_delete_plan'),
    path('admin/user-plans/', admin_views.admin_user_plans, name='admin_user_plans'),
    path('admin/user-plans/<int:plan_id>/toggle/', admin_views.admin_toggle_user_plan, name='admin_toggle_user_plan'),
    path('admin/user-plans/<int:plan_id>/add-profit/', admin_views.admin_add_profit, name='admin_add_profit'),
    path('admin/projects/', admin_views.admin_projects, name='admin_projects'),
    path('admin/projects/create/', admin_views.admin_create_project, name='admin_create_project'),
    path('admin/projects/<int:project_id>/update-status/', admin_views.admin_update_project_status, name='admin_update_project_status'),
    path('admin/projects/<int:project_id>/edit/', admin_views.admin_edit_project, name='admin_edit_project'),
    path('admin/projects/<int:project_id>/delete/', admin_views.admin_delete_project, name='admin_delete_project'),
    path('admin/assets/', admin_views.admin_assets, name='admin_assets'),
    path('admin/assets/create/', admin_views.admin_create_asset, name='admin_create_asset'),
    path('admin/assets/<int:asset_id>/toggle/', admin_views.admin_toggle_asset, name='admin_toggle_asset'),
    path('admin/assets/<int:asset_id>/update-price/', admin_views.admin_update_asset_price, name='admin_update_asset_price'),
    path('admin/assets/<int:asset_id>/edit/', admin_views.admin_edit_asset, name='admin_edit_asset'),
    path('admin/assets/<int:asset_id>/delete/', admin_views.admin_delete_asset, name='admin_delete_asset'),
    path('admin/payment-methods/', admin_views.admin_payment_methods, name='admin_payment_methods'),
    path('admin/payment-methods/create/', admin_views.admin_create_payment_method, name='admin_create_payment_method'),
    path('admin/payment-methods/<int:method_id>/toggle/', admin_views.admin_toggle_payment_method, name='admin_toggle_payment_method'),
    path('admin/payment-methods/<int:method_id>/edit/', admin_views.admin_edit_payment_method, name='admin_edit_payment_method'),
    path('admin/payment-methods/<int:method_id>/delete/', admin_views.admin_delete_payment_method, name='admin_delete_payment_method'),
]