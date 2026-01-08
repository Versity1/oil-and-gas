from django.shortcuts import render

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
    return render(request, 'login.html')

def register(request):
    return render(request, 'register.html')

def password_reset(request):
    return render(request, 'password_reset.html')

# Dashboard Pages
def dashboard(request):
    return render(request, 'dashboard.html')

def investment_plan(request):
    return render(request, 'investment-plan.html')

def shares(request):
    return render(request, 'shares.html')

def transaction_history(request):
    return render(request, 'transaction-history.html')

def deposit(request):
    return render(request, 'deposit.html')

def withdrawal(request):
    return render(request, 'withdrawal.html')