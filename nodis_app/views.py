from django.shortcuts import render


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