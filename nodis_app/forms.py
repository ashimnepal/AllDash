from django import forms

from .models import (
    AlertRecipient,
    Budget,
    Expense,
    FamilyMember,
    FamilyPortfolioHolding,
    Income,
    MoneyToGet,
    MoneyToPay,
    NepalSavingsTransaction,
    PortfolioHolding,
    PriceAlert,
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
    """Matches the 'Add' modal on the Money To Pay sidebar."""

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
                "id": "money-to-pay-amount",
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


class PortfolioHoldingForm(forms.ModelForm):
    """Matches the add/edit modals on the stock exchange 'My Portfolio' sidebar."""

    class Meta:
        model = PortfolioHolding
        fields = ["symbol", "company_name", "quantity", "buy_price", "buy_date"]
        widgets = {
            "symbol": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Symbol",
            }),
            "company_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Company name",
            }),
            "quantity": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Quantity",
                "step": "1",
                "min": "1",
            }),
            "buy_price": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Buy price",
                "step": "0.01",
                "min": "0.01",
            }),
            "buy_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
        }
        labels = {
            "company_name": "Company name (optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company_name"].required = False

    def clean_symbol(self):
        return self.cleaned_data["symbol"].strip().upper()


class FamilyMemberForm(forms.ModelForm):
    """Matches the 'Add Family Member' modal above the Family Portfolios accordion."""

    class Meta:
        model = FamilyMember
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Family member's name",
            }),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class FamilyPortfolioHoldingForm(forms.ModelForm):
    """Matches the add/edit holding modals inside each family member's accordion panel."""

    class Meta:
        model = FamilyPortfolioHolding
        fields = ["family_member", "symbol", "company_name", "quantity", "buy_price", "buy_date"]
        widgets = {
            "family_member": forms.HiddenInput(),
            "symbol": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Symbol",
            }),
            "company_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Company name",
            }),
            "quantity": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Quantity",
                "step": "1",
                "min": "1",
            }),
            "buy_price": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Buy price",
                "step": "0.01",
                "min": "0.01",
            }),
            "buy_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
        }
        labels = {
            "company_name": "Company name (optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company_name"].required = False

    def clean_symbol(self):
        return self.cleaned_data["symbol"].strip().upper()


class PriceAlertForm(forms.ModelForm):
    """Matches the add/edit modals on the stock exchange 'Price Alerts' card.

    `recipient` picks an existing AlertRecipient; `new_recipient_name`/`new_recipient_phone`
    let the same modal create (or update the number of) a recipient inline instead, so a user
    can type e.g. 'Ashmita' + her WhatsApp number once and reuse her from the dropdown after.
    """

    recipient = forms.ModelChoiceField(
        queryset=AlertRecipient.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    new_recipient_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Recipient's name"}),
    )
    new_recipient_phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "WhatsApp number, e.g. +9779800000000"}),
    )

    class Meta:
        model = PriceAlert
        fields = ["symbol", "company_name", "action", "target_price"]
        widgets = {
            "symbol": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Symbol",
            }),
            "company_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Company name",
            }),
            "action": forms.Select(attrs={
                "class": "form-select",
            }),
            "target_price": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Target price",
                "step": "0.01",
                "min": "0.01",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company_name"].required = False

    def clean_symbol(self):
        return self.cleaned_data["symbol"].strip().upper()

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get("new_recipient_name") or "").strip()
        phone = (cleaned.get("new_recipient_phone") or "").strip()
        if name and not phone:
            self.add_error("new_recipient_phone", "Enter a WhatsApp number for the new recipient.")
        if phone and not name:
            self.add_error("new_recipient_name", "Enter a name for the new recipient.")
        return cleaned

    def resolve_recipient(self):
        """Call after is_valid(): returns the AlertRecipient to attach, creating/updating one if
        a new name+phone were typed instead of an existing recipient being picked from the list."""
        name = (self.cleaned_data.get("new_recipient_name") or "").strip()
        phone = (self.cleaned_data.get("new_recipient_phone") or "").strip()
        if name and phone:
            recipient, created = AlertRecipient.objects.get_or_create(
                name=name, defaults={"phone_number": phone}
            )
            if not created and recipient.phone_number != phone:
                recipient.phone_number = phone
                recipient.save(update_fields=["phone_number"])
            return recipient
        return self.cleaned_data.get("recipient")


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
        ("NPR", "NPR"),
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
