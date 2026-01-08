from django.shortcuts import render

# Front Pages
def home(request):
    return render(request, 'core_app/home.html')

def about(request):
    return render(request, 'core_app/about.html')

def services(request):
    return render(request, 'core_app/services.html')

def contact(request):
    return render(request, 'core_app/contact.html')

def products(request):
    return render(request, 'core_app/products.html')

# Auth Pages
def login_view(request):
    return render(request, 'core_app/login.html')

def register(request):
    return render(request, 'core_app/register.html')

def password_reset(request):
    return render(request, 'core_app/password_reset.html')

# Dashboard Pages
def dashboard(request):
    return render(request, 'core_app/dashboard.html')

def investment_plan(request):
    return render(request, 'core_app/investment-plan.html')

def shares(request):
    return render(request, 'core_app/shares.html')

def transaction_history(request):
    return render(request, 'core_app/transaction-history.html')

def deposit(request):
    return render(request, 'core_app/deposit.html')

def withdrawal(request):
    return render(request, 'core_app/withdrawal.html')