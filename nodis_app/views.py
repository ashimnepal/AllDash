import requests
from django.http import JsonResponse
from django.shortcuts import render

NEPSE_API_BASE = "http://192.168.5.182:8000"
WATCHLIST_SYMBOLS = {"NABIL", "NICA", "HIDCL", "NHPC", "UPPER", "CHCL", "SHIVM"}


def home(request):
    return render(request, 'body/Dashboard/Dashboard.html')

def league(request):
    return render(request, 'body/pages/premierleague/PremierLeague.html')

def motogp(request):
    return render(request, 'body/pages/motogp/motodash.html')

def formula1(request):
    return render(request, 'body/pages/formula1/f1_home.html')
    
def expensetracking(request):
    return render(request, 'body/pages/expense_tracking/expensetracking_dash.html')

def stockex(request):
    return render(request, 'body/pages/stockex/stockex_dash.html')


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

    watchlist = [
        {
            "symbol": s["symbol"],
            "price": s["lastTradedPrice"],
            "changePercent": s["percentageChange"],
            "volume": s["totalTradeQuantity"],
        }
        for s in price_volume_data
        if s.get("symbol") in WATCHLIST_SYMBOLS
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