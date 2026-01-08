from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import UserRegistrationForm

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