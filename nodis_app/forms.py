from django import forms

from .models import (
    Budget,
    Expense,
    Income,
    MoneyToGet,
    MoneyToPay,
    NepalSavingsTransaction,
)


class ExpenseForm(forms.ModelForm):
    """Matches the 'Add a new expense' card on the expense tracking page."""

    class Meta:
        model = Expense
        fields = ["name", "category", "amount", "date"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "id": "expense-name",
                "placeholder": "Expense name",
            }),
            "category": forms.Select(attrs={
                "class": "form-select",
                "id": "expense-category",
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "id": "expense-amount",
                "placeholder": "Amount",
                "step": "0.01",
                "min": "0.01",
            }),
            "date": forms.DateInput(attrs={
                "class": "form-control",
                "id": "expense-date",
                "type": "date",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].empty_label = "Select category"
        self.fields["category"].required = False


class IncomeForm(forms.ModelForm):
    """Matches the 'Add Income' modal."""

    class Meta:
        model = Income
        fields = ["amount", "source"]
        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "id": "income-amount",
                "placeholder": "Amount",
                "step": "0.01",
                "min": "0.01",
            }),
            "source": forms.TextInput(attrs={
                "class": "form-control",
                "id": "income-source",
                "placeholder": "Source",
            }),
        }
        labels = {
            "source": "Source (optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source"].required = False


class BudgetForm(forms.ModelForm):
    """Sets the monthly budget shown in the 'Monthly budget' stat card."""

    class Meta:
        model = Budget
        fields = ["month", "amount"]
        widgets = {
            "month": forms.DateInput(attrs={
                "class": "form-control",
                "id": "budget-month",
                "type": "month",
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "id": "budget-amount",
                "placeholder": "Amount",
                "step": "0.01",
                "min": "0.01",
            }),
        }


class MoneyToGetForm(forms.ModelForm):
    """Matches the 'Edit Amount' modal on the Money To Get sidebar."""

    class Meta:
        model = MoneyToGet
        fields = ["name", "amount"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "id": "money-to-get-name",
                "placeholder": "Name",
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "id": "edit-money-to-get-amount",
                "placeholder": "Amount",
                "step": "0.01",
                "min": "0.01",
            }),
        }


class MoneyToPayForm(forms.ModelForm):
    """Matches the 'Edit Amount' modal on the Money To Pay sidebar."""

    class Meta:
        model = MoneyToPay
        fields = ["name", "amount"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "id": "money-to-pay-name",
                "placeholder": "Name",
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "id": "edit-money-to-pay-amount",
                "placeholder": "Amount",
                "step": "0.01",
                "min": "0.01",
            }),
        }


class NepalSavingsTransactionForm(forms.ModelForm):
    """Base form for a Nepal Savings entry (amount + optional note).

    The 'type' and 'date' are not visible inputs on the page - the view sets
    them based on which modal was submitted / the current date.
    """

    class Meta:
        model = NepalSavingsTransaction
        fields = ["amount", "note"]
        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Amount",
                "step": "0.01",
                "min": "0.01",
            }),
            "note": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Note",
            }),
        }
        labels = {
            "note": "Note (optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note"].required = False


class NepalSavingsAddForm(NepalSavingsTransactionForm):
    """Matches the 'Add Savings' modal (savings-amount / savings-note fields)."""

    class Meta(NepalSavingsTransactionForm.Meta):
        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "id": "savings-amount",
                "placeholder": "Amount",
                "step": "0.01",
                "min": "0.01",
            }),
            "note": forms.TextInput(attrs={
                "class": "form-control",
                "id": "savings-note",
                "placeholder": "Note",
            }),
        }


class NepalSavingsUseForm(NepalSavingsTransactionForm):
    """Matches the 'Money Used' modal (usage-amount / usage-note fields)."""

    class Meta(NepalSavingsTransactionForm.Meta):
        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "id": "usage-amount",
                "placeholder": "Amount",
                "step": "0.01",
                "min": "0.01",
            }),
            "note": forms.TextInput(attrs={
                "class": "form-control",
                "id": "usage-note",
                "placeholder": "Note",
            }),
        }


class CurrencyConverterForm(forms.Form):
    """Matches the standalone currency converter widget on the expense tracking page."""

    FROM_CURRENCY_CHOICES = [
        ("CAD", "CAD"),
        ("USD", "USD"),
        ("EUR", "EUR"),
        ("GBP", "GBP"),
        ("INR", "INR"),
    ]
    TO_CURRENCY_CHOICES = [
        ("CAD", "CAD"),
        ("USD", "USD"),
        ("INR", "NPR"),
    ]

    amount = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        initial=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "id": "converter-amount",
            "placeholder": "Amount",
        }),
    )
    from_currency = forms.ChoiceField(
        choices=FROM_CURRENCY_CHOICES,
        initial="CAD",
        widget=forms.Select(attrs={"class": "form-select", "id": "converter-from"}),
    )
    to_currency = forms.ChoiceField(
        choices=TO_CURRENCY_CHOICES,
        initial="USD",
        widget=forms.Select(attrs={"class": "form-select", "id": "converter-to"}),
    )
