from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

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
]