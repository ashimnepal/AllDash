from django.shortcuts import render, redirect
from django.views import View

from .forms import (
    CurrencyConverterForm,
    ExpenseForm,
    IncomeForm,
    MoneyToGetForm,
    MoneyToPayForm,
    NepalSavingsAddForm,
    NepalSavingsUseForm,
)


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

    def get_context(self, expense_form=None, income_form=None):
        return {
            'expense_form': expense_form or ExpenseForm(),
            'income_form': income_form or IncomeForm(),
            'converter_form': CurrencyConverterForm(),
            'money_to_get_form': MoneyToGetForm(),
            'money_to_pay_form': MoneyToPayForm(),
            'nepal_add_form': NepalSavingsAddForm(),
            'nepal_use_form': NepalSavingsUseForm(),
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context())

    def post(self, request):
        expense_form = ExpenseForm()
        income_form = IncomeForm()

        if 'expense_submit' in request.POST:
            expense_form = ExpenseForm(request.POST)
            if expense_form.is_valid():
                expense_form.save()
                return redirect('expensetrackingpage')
        elif 'income_submit' in request.POST:
            income_form = IncomeForm(request.POST)
            if income_form.is_valid():
                income_form.save()
                return redirect('expensetrackingpage')

        return render(request, self.template_name, self.get_context(expense_form, income_form))



def stockex(request):
    return render(request, 'body/pages/stockex/stockex_dash.html')