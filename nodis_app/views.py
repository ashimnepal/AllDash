import random
from datetime import date

import requests
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST

from .forms import (
    CurrencyConverterForm,
    ExpenseForm,
    IncomeForm,
    MoneyToGetForm,
    MoneyToPayForm,
    NepalSavingsAddForm,
    NepalSavingsUseForm,
    PortfolioHoldingForm,
    PriceAlertForm,
)
from .models import Budget, Expense, Income, MoneyToGet, MoneyToPay
from .models import NepalSavingsTransaction, PortfolioHolding, PriceAlert

# Chip/legend colour used per category slug on the expense tracking page.
CATEGORY_STYLES = {
    "food": {"chip": "chip-soft-success", "legend": "legend-primary"},
    "utilities": {"chip": "chip-soft-warning", "legend": "legend-warning"},
    "transport": {"chip": "chip-soft-secondary", "legend": "legend-success"},
    "leisure": {"chip": "chip-soft-danger", "legend": "legend-danger"},
    "subscriptions": {"chip": "chip-soft-info", "legend": "legend-info"},
}
DEFAULT_CATEGORY_STYLE = {"chip": "chip-soft-secondary", "legend": "legend-secondary"}

NEPSE_API_BASE = "http://192.168.5.182:8000"
# Which real NEPSE sectorName values feed each 'My Watchlist' category pill.
WATCHLIST_SECTOR_CATEGORIES = {
    "Commercial Banks": "Banking",
    "Hydro Power": "Hydro",
    "Life Insurance": "Insurance",
    "Non Life Insurance": "Insurance",
    "Manufacturing And Processing": "Manufacturing",
}
COMPANY_LIST_CACHE_KEY = 'nepse_company_list'
COMPANY_LIST_CACHE_TTL = 6 * 60 * 60  # the company registry barely changes, cache it longer


def home(request):
    return render(request, 'body/Dashboard/Dashboard.html')

def league(request):
    return render(request, 'body/pages/premierleague/PremierLeague.html')

def motogp(request):
    return render(request, 'body/pages/motogp/motodash.html')

def formula1(request):
    return render(request, 'body/pages/formula1/f1_home.html')


class ExpenseTrackingView(View):
    template_name = 'body/pages/expense_tracking/expensetracking_dash.html'

    @staticmethod
    def format_expense_date(value):
        if not hasattr(value, 'strftime'):
            return str(value)
        return '{} {}'.format(value.strftime('%b'), value.day)

    def format_expense_rows(self, queryset):
        rows = []
        for expense in queryset:
            slug = expense.category.slug if expense.category else None
            style = CATEGORY_STYLES.get(slug, DEFAULT_CATEGORY_STYLE)
            rows.append({
                'name': expense.name,
                'category_name': expense.category.name if expense.category else 'Uncategorized',
                'chip_class': style['chip'],
                'amount': float(expense.amount),
                'date': self.format_expense_date(expense.date),
            })
        return rows

    def get_available_months(self):
        months = list(
            Expense.objects.annotate(month=TruncMonth('date'))
            .values_list('month', flat=True)
            .distinct()
            .order_by('-month')
        )
        today_month = date.today().replace(day=1)
        if today_month not in months:
            months.insert(0, today_month)
            months.sort(reverse=True)
        return [
            {'value': m.strftime('%Y-%m'), 'label': m.strftime('%B %Y')}
            for m in months
        ]

    def compute_stats(self):
        today = date.today()

        expenses = Expense.objects.select_related('category').all()
        month_expenses = expenses.filter(date__year=today.year, date__month=today.month).all()

        spent_so_far = month_expenses.aggregate(total=Sum('amount'))['total'] or 0
        budget = Budget.objects.filter(month__year=today.year, month__month=today.month).first()
        income_this_month = Income.objects.filter(
            date__year=today.year, date__month=today.month
        ).aggregate(total=Sum('amount'))['total'] or 0
        budget_amount = (budget.amount if budget else 0) + income_this_month
        remaining = budget_amount - spent_so_far
        budget_used_percent = int(min(100, max(0, (spent_so_far / budget_amount * 100)))) if budget_amount else 0
        savings_goal_percent = max(0, 100 - budget_used_percent) if budget_amount else 0

        expense_rows = []
        for expense in expenses:
            slug = expense.category.slug if expense.category else None
            style = CATEGORY_STYLES.get(slug, DEFAULT_CATEGORY_STYLE)
            expense_rows.append({
                'name': expense.name,
                'category_name': expense.category.name if expense.category else 'Uncategorized',
                'chip_class': style['chip'],
                'amount': expense.amount,
                'date': expense.date,
            })

        category_totals = (
            month_expenses.values('category__name', 'category__slug')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )
        distribution = []
        if spent_so_far:
            for row in category_totals[:4]:
                style = CATEGORY_STYLES.get(row['category__slug'], DEFAULT_CATEGORY_STYLE)
                distribution.append({
                    'name': row['category__name'] or 'Uncategorized',
                    'legend_class': style['legend'],
                    'percent': round(row['total'] / spent_so_far * 100),
                })

        return {
            'expenses': expense_rows,
            'budget_amount': budget_amount,
            'spent_so_far': spent_so_far,
            'remaining': remaining,
            'budget_used_percent': budget_used_percent,
            'savings_goal_percent': savings_goal_percent,
            'distribution': distribution,
        }

    def get_context(self, expense_form=None, income_form=None):
        context = {
            'expense_form': expense_form or ExpenseForm(),
            'income_form': income_form or IncomeForm(),
            'converter_form': CurrencyConverterForm(),
            'money_to_get_form': MoneyToGetForm(),
            'money_to_pay_form': MoneyToPayForm(),
            'nepal_add_form': NepalSavingsAddForm(),
            'nepal_use_form': NepalSavingsUseForm(),
            'available_months': self.get_available_months(),
            'current_month_label': date.today().strftime('%B %Y'),
            'money_to_get_entries': MoneyToGet.objects.all(),
            'money_to_get_total': MoneyToGet.objects.aggregate(total=Sum('amount'))['total'] or 0,
            'money_to_pay_entries': MoneyToPay.objects.all(),
            'money_to_pay_total': MoneyToPay.objects.aggregate(total=Sum('amount'))['total'] or 0,
            'nepal_transactions': NepalSavingsTransaction.objects.all(),
            'nepal_total': self.compute_nepal_savings_total(),
        }
        context.update(self.compute_stats())
        return context

    def compute_nepal_savings_total(self):
        totals = NepalSavingsTransaction.objects.aggregate(
            added=Sum('amount', filter=Q(type=NepalSavingsTransaction.ADDED)),
            used=Sum('amount', filter=Q(type=NepalSavingsTransaction.USED)),
        )
        return (totals['added'] or 0) - (totals['used'] or 0)

    @staticmethod
    def is_ajax(request):
        return request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def month_json(self, month_param):
        if not month_param or month_param == 'all':
            rows = self.format_expense_rows(
                Expense.objects.select_related('category').all()
            )
            return JsonResponse({
                'success': True,
                'expenses': rows,
                'month_label': 'All months',
                'has_data': bool(rows),
            })

        try:
            year_str, month_str = month_param.split('-')
            year, month = int(year_str), int(month_str)
            month_label = date(year, month, 1).strftime('%B %Y')
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'Invalid month.'}, status=400)

        queryset = (
            Expense.objects.select_related('category')
            .filter(date__year=year, date__month=month)
            .order_by('-date', '-created_at')
        )
        rows = self.format_expense_rows(queryset)
        return JsonResponse({
            'success': True,
            'expenses': rows,
            'month_label': month_label,
            'has_data': bool(rows),
        })

    def get(self, request):
        if self.is_ajax(request) and 'month' in request.GET:
            return self.month_json(request.GET.get('month'))
        return render(request, self.template_name, self.get_context())

    def stats_json(self, extra=None):
        stats = self.compute_stats()
        data = {
            'budget_amount': float(stats['budget_amount']),
            'spent_so_far': float(stats['spent_so_far']),
            'remaining': float(stats['remaining']),
            'budget_used_percent': stats['budget_used_percent'],
            'savings_goal_percent': stats['savings_goal_percent'],
            'distribution': stats['distribution'],
            'expenses': [
                {
                    'name': row['name'],
                    'category_name': row['category_name'],
                    'chip_class': row['chip_class'],
                    'amount': float(row['amount']),
                    'date': self.format_expense_date(row['date']),
                }
                for row in stats['expenses']
            ],
        }
        if extra:
            data.update(extra)
        return data

    def post(self, request):
        ajax = self.is_ajax(request)
        expense_form = ExpenseForm()
        income_form = IncomeForm()

        if 'expense_submit' in request.POST:
            expense_form = ExpenseForm(request.POST)
            if expense_form.is_valid():
                expense_form.save()
                if ajax:
                    return JsonResponse(self.stats_json({
                        'success': True,
                        'message': 'Expense added successfully.',
                    }))
                messages.success(request, 'Expense added successfully.')
                return redirect('expensetrackingpage')
            if ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Please fix the errors in the expense form.',
                    'errors': {field: [str(e) for e in errs] for field, errs in expense_form.errors.items()},
                }, status=400)
            messages.error(request, 'Please fix the errors in the expense form.')
        elif 'income_submit' in request.POST:
            income_form = IncomeForm(request.POST)
            if income_form.is_valid():
                income_form.save()
                if ajax:
                    return JsonResponse(self.stats_json({
                        'success': True,
                        'message': 'Income added successfully.',
                    }))
                messages.success(request, 'Income added successfully.')
                return redirect('expensetrackingpage')
            if ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Please fix the errors in the income form.',
                    'errors': {field: [str(e) for e in errs] for field, errs in income_form.errors.items()},
                }, status=400)
            messages.error(request, 'Please fix the errors in the income form.')

        return render(request, self.template_name, self.get_context(expense_form, income_form))


def money_to_pay_json(extra=None):
    entries = MoneyToPay.objects.all()
    data = {
        'entries': [
            {'id': entry.id, 'name': entry.name, 'amount': float(entry.amount)}
            for entry in entries
        ],
        'total': float(entries.aggregate(total=Sum('amount'))['total'] or 0),
    }
    if extra:
        data.update(extra)
    return data


def nepal_savings_json(extra=None):
    transactions = NepalSavingsTransaction.objects.all()
    data = {
        'transactions': [
            {
                'id': tx.id,
                'type': tx.type,
                'amount': float(tx.amount),
                'note': tx.note,
                'date': tx.date.isoformat(),
            }
            for tx in transactions
        ],
        'total': float(
            (
                transactions.filter(type=NepalSavingsTransaction.ADDED).aggregate(total=Sum('amount'))['total'] or 0
            ) - (
                transactions.filter(type=NepalSavingsTransaction.USED).aggregate(total=Sum('amount'))['total'] or 0
            )
        ),
    }
    if extra:
        data.update(extra)
    return data


@require_POST
def nepal_savings_update(request, pk):
    transaction = get_object_or_404(NepalSavingsTransaction, pk=pk)
    form = NepalSavingsAddForm(request.POST, instance=transaction)
    if form.is_valid():
        tx = form.save(commit=False)
        tx.type = transaction.type
        tx.date = transaction.date
        tx.save()
        return JsonResponse(nepal_savings_json({'success': True, 'message': 'Transaction updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def nepal_savings_delete(request, pk):
    transaction = get_object_or_404(NepalSavingsTransaction, pk=pk)
    transaction.delete()
    return JsonResponse(nepal_savings_json({'success': True, 'message': 'Transaction deleted.'}))


@require_POST
def nepal_savings_add(request):
    form = NepalSavingsAddForm(request.POST)
    if form.is_valid():
        tx = form.save(commit=False)
        tx.type = NepalSavingsTransaction.ADDED
        tx.date = date.today()
        tx.save()
        return JsonResponse(nepal_savings_json({'success': True, 'message': 'Savings added.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def nepal_savings_use(request):
    form = NepalSavingsUseForm(request.POST)
    if form.is_valid():
        tx = form.save(commit=False)
        tx.type = NepalSavingsTransaction.USED
        tx.date = date.today()
        tx.save()
        return JsonResponse(nepal_savings_json({'success': True, 'message': 'Money used.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


def money_to_get_json(extra=None):
    entries = MoneyToGet.objects.all()
    data = {
        'entries': [
            {'id': entry.id, 'name': entry.name, 'amount': float(entry.amount)}
            for entry in entries
        ],
        'total': float(entries.aggregate(total=Sum('amount'))['total'] or 0),
    }
    if extra:
        data.update(extra)
    return data


@require_POST
def money_to_get_add(request):
    form = MoneyToGetForm(request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse(money_to_get_json({'success': True, 'message': 'Entry added.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def money_to_get_update(request, pk):
    entry = get_object_or_404(MoneyToGet, pk=pk)
    form = MoneyToGetForm(request.POST, instance=entry)
    if form.is_valid():
        form.save()
        return JsonResponse(money_to_get_json({'success': True, 'message': 'Entry updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def money_to_get_delete(request, pk):
    entry = get_object_or_404(MoneyToGet, pk=pk)
    entry.delete()
    return JsonResponse(money_to_get_json({'success': True, 'message': 'Entry removed.'}))


@require_POST
def money_to_pay_add(request):
    form = MoneyToPayForm(request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse(money_to_pay_json({'success': True, 'message': 'Entry added.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def money_to_pay_update(request, pk):
    entry = get_object_or_404(MoneyToPay, pk=pk)
    form = MoneyToPayForm(request.POST, instance=entry)
    if form.is_valid():
        form.save()
        return JsonResponse(money_to_pay_json({'success': True, 'message': 'Entry updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def money_to_pay_delete(request, pk):
    entry = get_object_or_404(MoneyToPay, pk=pk)
    entry.delete()
    return JsonResponse(money_to_pay_json({'success': True, 'message': 'Entry removed.'}))


def stockex(request):
    context = portfolio_json()
    context.update(price_alerts_json())
    context.update(watchlist_json())
    return render(request, 'body/pages/stockex/stockex_dash.html', context)


def _format_nepali_amount(value):
    """Format a raw Rs amount using Lakh/Crore/Arba/Kharba units."""
    value = float(value or 0)
    if value >= 1e11:
        return f"Rs {value / 1e11:.2f} Kharba"
    if value >= 1e9:
        return f"Rs {value / 1e9:.2f} Arba"
    if value >= 1e7:
        return f"Rs {value / 1e7:.2f} Crore"
    if value >= 1e5:
        return f"Rs {value / 1e5:.2f} Lakh"
    return f"Rs {value:,.2f}"


PORTFOLIO_PRICE_CACHE_KEY = 'nepse_price_volume_map'
PORTFOLIO_PRICE_CACHE_TTL = 60  # NEPSE prices tick constantly; keep this short


def get_nepse_price_map():
    """Symbol -> {name, price, change_percent, volume} from the LAN NEPSE PriceVolume feed, cached briefly."""
    price_map = cache.get(PORTFOLIO_PRICE_CACHE_KEY)
    if price_map is not None:
        return price_map

    response = requests.get(f"{NEPSE_API_BASE}/PriceVolume", timeout=5)
    response.raise_for_status()
    price_map = {
        row["symbol"]: {
            "name": (row.get("securityName") or "").strip(),
            "price": row.get("lastTradedPrice"),
            "change_percent": row.get("percentageChange"),
            "volume": row.get("totalTradeQuantity"),
        }
        for row in response.json()
        if row.get("symbol")
    }
    cache.set(PORTFOLIO_PRICE_CACHE_KEY, price_map, PORTFOLIO_PRICE_CACHE_TTL)
    return price_map


def get_watchlist_symbols():
    """Every active equity in our watched sectors, symbol -> {company, category}, sourced from /CompanyList."""
    companies = cache.get(COMPANY_LIST_CACHE_KEY)
    if companies is None:
        response = requests.get(f"{NEPSE_API_BASE}/CompanyList", timeout=5)
        response.raise_for_status()
        companies = response.json()
        cache.set(COMPANY_LIST_CACHE_KEY, companies, COMPANY_LIST_CACHE_TTL)

    symbols = {}
    for row in companies:
        category = WATCHLIST_SECTOR_CATEGORIES.get(row.get("sectorName"))
        if not category or row.get("status") != "A" or row.get("instrumentType") != "Equity":
            continue
        symbol = row.get("symbol")
        if not symbol or symbol in symbols:
            continue
        symbols[symbol] = {
            "company": (row.get("companyName") or row.get("securityName") or "").strip(),
            "category": category,
        }
    return symbols


def _watchlist_sparkline(symbol, change_percent):
    """Deterministic pseudo 7D trend line (no historical feed available), seeded per symbol."""
    rng = random.Random(symbol)
    trending_up = (change_percent or 0) >= 0
    value = 15.0
    points = [value]
    for _ in range(10):
        drift = rng.uniform(0.5, 2.5) * (1 if trending_up else -1)
        value = max(2.0, value + drift + rng.uniform(-1, 1))
        points.append(round(value, 1))
    return ",".join(str(p) for p in points)


def watchlist_json():
    """Watchlist rows (with live price/change/volume) plus the distinct category list."""
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        price_map = {}
    try:
        watchlist_symbols = get_watchlist_symbols()
    except (requests.RequestException, ValueError):
        watchlist_symbols = {}

    rows = []
    categories = []
    for symbol, meta in watchlist_symbols.items():
        info = price_map.get(symbol)
        change_percent = info["change_percent"] if info else None
        rows.append({
            "symbol": symbol,
            "company": meta["company"],
            "category": meta["category"],
            "price": info["price"] if info else None,
            "change_percent": change_percent,
            "volume": info["volume"] if info else None,
            "sparkline": _watchlist_sparkline(symbol, change_percent),
        })
        if meta["category"] not in categories:
            categories.append(meta["category"])

    return {"watchlist": rows, "watchlist_categories": categories}


def portfolio_symbols(request):
    """List of tradable symbols/names/prices for the 'select stock' dropdown on the portfolio modal."""
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        return JsonResponse({"error": "NEPSE API is unreachable"}, status=502)

    symbols = [
        {"symbol": symbol, "name": info["name"], "price": info["price"]}
        for symbol, info in sorted(price_map.items())
    ]
    return JsonResponse({"symbols": symbols})


def portfolio_json(extra=None):
    """Holdings + totals payload shared by the page render and every portfolio CRUD response."""
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        price_map = {}

    rows = []
    total_invested = 0.0
    total_current = 0.0
    for holding in PortfolioHolding.objects.all():
        info = price_map.get(holding.symbol)
        current_price = float(info["price"]) if info and info.get("price") is not None else float(holding.buy_price)
        invested = float(holding.buy_price) * holding.quantity
        current_value = current_price * holding.quantity
        profit = current_value - invested
        profit_percent = (profit / invested * 100) if invested else 0.0
        total_invested += invested
        total_current += current_value
        rows.append({
            "id": holding.id,
            "symbol": holding.symbol,
            "company_name": holding.company_name or (info["name"] if info else ""),
            "quantity": holding.quantity,
            "buy_price": float(holding.buy_price),
            "current_price": current_price,
            "buy_date": holding.buy_date.isoformat(),
            "invested": invested,
            "current_value": current_value,
            "profit": profit,
            "profit_percent": profit_percent,
            "is_up": profit >= 0,
        })

    total_profit = total_current - total_invested
    total_profit_percent = (total_profit / total_invested * 100) if total_invested else 0.0
    data = {
        "holdings": rows,
        "total_invested": total_invested,
        "total_current": total_current,
        "total_profit": total_profit,
        "total_profit_percent": total_profit_percent,
    }
    if extra:
        data.update(extra)
    return data


@require_POST
def portfolio_add(request):
    form = PortfolioHoldingForm(request.POST)
    if form.is_valid():
        holding = form.save(commit=False)
        if not holding.company_name:
            try:
                info = get_nepse_price_map().get(holding.symbol)
                if info:
                    holding.company_name = info["name"]
            except (requests.RequestException, ValueError):
                pass
        holding.save()
        return JsonResponse(portfolio_json({'success': True, 'message': 'Holding added.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def portfolio_update(request, pk):
    holding = get_object_or_404(PortfolioHolding, pk=pk)
    form = PortfolioHoldingForm(request.POST, instance=holding)
    if form.is_valid():
        form.save()
        return JsonResponse(portfolio_json({'success': True, 'message': 'Holding updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def portfolio_delete(request, pk):
    holding = get_object_or_404(PortfolioHolding, pk=pk)
    holding.delete()
    return JsonResponse(portfolio_json({'success': True, 'message': 'Holding removed.'}))


def _price_alert_status(alert, current_price):
    """Row payload for a single alert, including its live current price and status text."""
    target = float(alert.target_price)
    if alert.is_triggered:
        if alert.triggered_direction == PriceAlert.UP:
            status_text = f"Crossed above Rs {target:,.2f}"
        else:
            status_text = f"Dropped below Rs {target:,.2f}"
    else:
        status_text = f"Alert when price hits Rs {target:,.2f}"
    return {
        "id": alert.id,
        "symbol": alert.symbol,
        "company_name": alert.company_name,
        "target_price": target,
        "current_price": current_price,
        "is_triggered": alert.is_triggered,
        "direction": alert.triggered_direction,
        "status_text": status_text,
        "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
    }


def price_alerts_json(extra=None):
    """Alerts list + active count payload shared by the page render and every alert CRUD response."""
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        price_map = {}

    rows = []
    active_count = 0
    for alert in PriceAlert.objects.all():
        info = price_map.get(alert.symbol)
        current_price = float(info["price"]) if info and info.get("price") is not None else float(alert.last_price or alert.target_price)
        if not alert.is_triggered:
            active_count += 1
        rows.append(_price_alert_status(alert, current_price))

    data = {"price_alerts": rows, "price_alerts_active_count": active_count}
    if extra:
        data.update(extra)
    return data


@require_POST
def price_alert_add(request):
    form = PriceAlertForm(request.POST)
    if form.is_valid():
        alert = form.save(commit=False)
        try:
            info = get_nepse_price_map().get(alert.symbol)
        except (requests.RequestException, ValueError):
            info = None
        if info:
            alert.last_price = info["price"]
            if not alert.company_name:
                alert.company_name = info["name"]
        alert.save()
        return JsonResponse(price_alerts_json({'success': True, 'message': 'Alert created.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def price_alert_update(request, pk):
    alert = get_object_or_404(PriceAlert, pk=pk)
    form = PriceAlertForm(request.POST, instance=alert)
    if form.is_valid():
        alert = form.save(commit=False)
        # Editing re-arms the alert with a fresh baseline price.
        alert.is_triggered = False
        alert.triggered_direction = ""
        alert.triggered_at = None
        try:
            info = get_nepse_price_map().get(alert.symbol)
        except (requests.RequestException, ValueError):
            info = None
        alert.last_price = info["price"] if info else None
        alert.save()
        return JsonResponse(price_alerts_json({'success': True, 'message': 'Alert updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def price_alert_delete(request, pk):
    alert = get_object_or_404(PriceAlert, pk=pk)
    alert.delete()
    return JsonResponse(price_alerts_json({'success': True, 'message': 'Alert removed.'}))


def price_alerts_check(request):
    """Polled by the dashboard: evaluates active alerts and flags any that just crossed their target."""
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        return JsonResponse(price_alerts_json({'triggered': []}))

    triggered_now = []
    for alert in PriceAlert.objects.filter(is_triggered=False):
        info = price_map.get(alert.symbol)
        if not info or info.get("price") is None:
            continue
        current_price = float(info["price"])
        target = float(alert.target_price)
        last_price = float(alert.last_price) if alert.last_price is not None else None

        if last_price is None:
            alert.last_price = current_price
            alert.save(update_fields=["last_price"])
            continue

        crossed_up = last_price < target <= current_price
        crossed_down = last_price > target >= current_price
        if crossed_up or crossed_down:
            alert.is_triggered = True
            alert.triggered_direction = PriceAlert.UP if crossed_up else PriceAlert.DOWN
            alert.triggered_at = timezone.now()
            alert.last_price = current_price
            alert.save()
            triggered_now.append(_price_alert_status(alert, current_price))
        else:
            alert.last_price = current_price
            alert.save(update_fields=["last_price"])

    return JsonResponse(price_alerts_json({'triggered': triggered_now}))


def nepse_live_data(request):
    """Proxy live NEPSE data from the Mac mini's REST API for the stock dashboard."""
    try:
        index_data = requests.get(f"{NEPSE_API_BASE}/NepseIndex", timeout=5).json()
        summary_data = requests.get(f"{NEPSE_API_BASE}/Summary", timeout=5).json()
        gainers_data = requests.get(f"{NEPSE_API_BASE}/TopGainers", timeout=5).json()
        losers_data = requests.get(f"{NEPSE_API_BASE}/TopLosers", timeout=5).json()
        price_volume_data = requests.get(f"{NEPSE_API_BASE}/PriceVolume", timeout=5).json()
    except (requests.RequestException, ValueError):
        return JsonResponse({"error": "Mac mini NEPSE API is unreachable"}, status=502)

    nepse_index = index_data.get("NEPSE Index", {})
    advances = sum(1 for s in price_volume_data if s.get("percentageChange", 0) > 0)
    declines = sum(1 for s in price_volume_data if s.get("percentageChange", 0) < 0)
    unchanged = sum(1 for s in price_volume_data if s.get("percentageChange", 0) == 0)

    try:
        watchlist_symbols = get_watchlist_symbols()
    except (requests.RequestException, ValueError):
        watchlist_symbols = {}

    watchlist = [
        {
            "symbol": s["symbol"],
            "price": s["lastTradedPrice"],
            "changePercent": s["percentageChange"],
            "volume": s["totalTradeQuantity"],
        }
        for s in price_volume_data
        if s.get("symbol") in watchlist_symbols
    ]

    data = {
        "index": {
            "value": nepse_index.get("currentValue"),
            "change": nepse_index.get("change"),
            "changePercent": nepse_index.get("perChange"),
            "high": nepse_index.get("high"),
            "low": nepse_index.get("low"),
            "prevClose": nepse_index.get("previousClose"),
        },
        "market": {
            "turnover": _format_nepali_amount(summary_data.get("Total Turnover Rs:")),
            "marketCap": _format_nepali_amount(summary_data.get("Total Market Capitalization Rs:")),
            "advances": advances,
            "declines": declines,
            "unchanged": unchanged,
        },
        "gainers": [
            {"symbol": g["symbol"], "company": g["securityName"], "price": g["ltp"], "changePercent": g["percentageChange"]}
            for g in gainers_data[:5]
        ],
        "losers": [
            {"symbol": l["symbol"], "company": l["securityName"], "price": l["ltp"], "changePercent": l["percentageChange"]}
            for l in losers_data[:5]
        ],
        "watchlist": watchlist,
    }
    return JsonResponse(data)


# Free-tier currencyapi.net keys only allow the /rates endpoint (base=USD), not
# /convert, so conversions are computed locally from USD-based rates.
CURRENCYAPI_NET_RATES_URL = 'https://currencyapi.net/api/v2/rates'
CURRENCYAPI_NET_RATES_CACHE_KEY = 'currencyapi_net_usd_rates'
CURRENCYAPI_NET_RATES_CACHE_TTL = 3600  # free plan refreshes rates hourly


def get_usd_rates():
    rates = cache.get(CURRENCYAPI_NET_RATES_CACHE_KEY)
    if rates is not None:
        return rates

    response = requests.get(
        CURRENCYAPI_NET_RATES_URL,
        params={'key': settings.CURRENCYAPI_NET_KEY, 'output': 'JSON'},
        timeout=5,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get('valid'):
        raise ValueError('currencyapi.net returned an invalid rates response')

    rates = payload['rates']
    rates['USD'] = 1.0
    cache.set(CURRENCYAPI_NET_RATES_CACHE_KEY, rates, CURRENCYAPI_NET_RATES_CACHE_TTL)
    return rates


@require_POST
def convert_currency(request):
    form = CurrencyConverterForm(request.POST)
    if not form.is_valid():
        return JsonResponse({
            'success': False,
            'message': 'Please fix the errors below.',
            'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
        }, status=400)

    if not settings.CURRENCYAPI_NET_KEY:
        return JsonResponse({
            'success': False,
            'message': 'Currency conversion is not configured. Missing API key.',
        }, status=500)

    amount = form.cleaned_data['amount']
    from_currency = form.cleaned_data['from_currency']
    to_currency = form.cleaned_data['to_currency']

    try:
        rates = get_usd_rates()
    except (requests.RequestException, ValueError):
        return JsonResponse({
            'success': False,
            'message': 'Could not reach the currency conversion service. Please try again later.',
        }, status=502)

    if from_currency not in rates or to_currency not in rates:
        return JsonResponse({
            'success': False,
            'message': 'One of the selected currencies is not supported.',
        }, status=400)

    amount_in_usd = float(amount) / rates[from_currency]
    result = amount_in_usd * rates[to_currency]
    return JsonResponse({
        'success': True,
        'amount': float(amount),
        'from_currency': from_currency,
        'to_currency': to_currency,
        'result': result,
        'message': '{:.2f} {} = {:.2f} {}'.format(float(amount), from_currency, result, to_currency),
    })
