from django.urls import path
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
    path('password-reset/', views.password_reset, name='password_reset'),
    
    # Dashboard Pages
    path('dashboard/', views.dashboard, name='dashboard'),
    path('investment-plan/', views.investment_plan, name='investment_plan'),
    path('shares/', views.shares, name='shares'),
    path('transaction-history/', views.transaction_history, name='transaction_history'),
    path('deposit/', views.deposit, name='deposit'),
    path('withdrawal/', views.withdrawal, name='withdrawal'),
]