# Techo Drill Innovation - Oil & Gas Investment Platform

A comprehensive Django-powered investment platform for oil and gas projects, featuring shares/bonds trading, investment plans, and a custom admin dashboard.

![Django](https://img.shields.io/badge/Django-5.0-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.x-06B6D4)

## 🚀 Features

### User Features
- **User Authentication** - Registration, login, password reset with email verification
- **Dashboard** - Portfolio overview with balances, investments, and quick actions
- **Dual Wallet System**
  - **Main Balance** - For deposits, withdrawals, and investing
  - **Trading Wallet** - Stores proceeds from shares/bonds sales
- **Investment Options**
  - **Shares & Bonds** - Buy/sell assets with real-time pricing
  - **Investment Plans** - Subscribe to automated daily profit plans
  - **Project Funding** - Invest in individual energy projects
- **Transactions**
  - Crypto deposits with multiple payment methods
  - Withdrawal requests with wallet address
  - Complete transaction history

### Admin Features (Custom Dashboard)
- **Overview Metrics**
  - User statistics, pending deposits/withdrawals
  - Financial totals, trading balances
- **Shares & Bonds Metrics**
  - Total assets, active positions
  - Unrealized P&L, market value
  - Top assets by investors
  - Recent trades
- **Full CRUD Operations**
  - Users (view, suspend, delete, adjust balance)
  - Deposits/Withdrawals (approve, reject)
  - Investment Plans (create, edit, toggle, delete)
  - Projects (create, edit, status update, delete)
  - Assets/Shares (create, edit, price update, toggle, delete)
  - Payment Methods (create, edit, toggle, delete)
- **User Plan Management**
  - Add daily profits manually
  - Complete/reactivate plans

## 🏗️ Tech Stack

- **Backend**: Django 5.0, Python 3.11+
- **Frontend**: TailwindCSS, Vanilla JavaScript
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Icons**: Material Symbols Outlined
- **Fonts**: Space Grotesk, Noto Sans

## 📁 Project Structure

```
oil-and-gas/
├── core_app/
│   ├── management/
│   │   └── commands/
│   │       ├── update_profits.py           # Daily profit processing
│   │       └── process_investment_completions.py  # Maturity payouts
│   ├── templates/
│   │   ├── custom_admin/                   # Admin dashboard templates
│   │   │   ├── dashboard.html
│   │   │   ├── users.html
│   │   │   ├── deposits.html
│   │   │   ├── withdrawals.html
│   │   │   ├── investment_plans.html
│   │   │   ├── projects.html
│   │   │   ├── assets.html
│   │   │   └── payment_methods.html
│   │   ├── dashboard.html                  # User dashboard
│   │   ├── shares.html                     # Trading interface
│   │   ├── investment_packages.html        # Plans listing
│   │   ├── investment_plan.html            # Projects listing
│   │   ├── deposit.html / withdrawal.html
│   │   └── ... (auth, front pages)
│   ├── models.py                           # Database models
│   ├── views.py                            # User-facing views
│   ├── admin_views.py                      # Custom admin views
│   ├── signals.py                          # Transaction signals
│   ├── utils.py                            # Email utilities
│   └── urls.py                             # URL routing
├── oil_and_gas/                            # Django project settings
├── media/                                  # User uploads
├── manage.py
├── requirements.txt
└── README.md
```

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/oil-and-gas.git
   cd oil-and-gas
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file with:
   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Frontend: http://localhost:8000
   - Custom Admin: http://localhost:8000/admin/
   - Django Admin: http://localhost:8000/django-admin/

## ⏰ Scheduled Tasks (Cron Jobs)

Set up these commands to run daily:

```bash
# Process daily profits for active investment plans
python manage.py update_profits

# Complete matured investments and payout to users
python manage.py process_investment_completions
```

## 📊 Models Overview

| Model | Description |
|-------|-------------|
| `Account` | User wallet with main balance and trading balance |
| `PaymentMethod` | Crypto payment options (BTC, ETH, USDT, etc.) |
| `Deposit` | Deposit requests with status tracking |
| `Withdrawal` | Withdrawal requests to external wallets |
| `Project` | Investable energy projects |
| `Asset` | Tradeable shares and bonds |
| `Investment` | User investments in projects/assets |
| `InvestmentPlan` | Subscription plans with daily returns |
| `UserPlan` | Active user subscriptions |
| `Transaction` | All transaction records |

## 🔐 Security Features

- CSRF protection on all forms
- Staff-only access for admin views (`@staff_member_required`)
- Password hashing with Django's auth system
- Email verification for password reset
- Atomic transactions for financial operations

## 📧 Email Notifications

Users receive emails for:
- Registration confirmation
- Deposit/withdrawal approvals
- Investment purchases
- Investment maturity and payouts

## 🎨 UI/UX Features

- **Responsive Design** - Mobile-first approach
- **Dark Mode Admin** - Easy on the eyes
- **Interactive Modals** - For editing and confirmations
- **Real-time Calculations** - Portfolio values, P&L
- **Progress Indicators** - Investment progress bars

## 📝 License

This project is proprietary software. All rights reserved.

## 👨‍💻 Author

Built with ❤️ for Techo Drill Innovation

---

*Last updated: January 2026*
