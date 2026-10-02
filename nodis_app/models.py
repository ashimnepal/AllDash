from datetime import date

from django.db import models


class Category(models.Model):
    """Expense category shown as a chip/tag on the expense table (Food, Utilities, etc.)."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Budget(models.Model):
    """Monthly budget target used for the 'Monthly budget' / 'Remaining' stat cards."""

    month = models.DateField(help_text="Any date within the budgeted month")
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-month"]
        constraints = [
            models.UniqueConstraint(fields=["month"], name="unique_budget_per_month"),
        ]

    def __str__(self):
        return f"Budget for {self.month:%B %Y}: {self.amount}"


class Expense(models.Model):
    """A single expense entry, as added via the 'Add a new expense' form."""

    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.name} - {self.amount} ({self.date})"


class Income(models.Model):
    """A single income entry, as added via the 'Add Income' modal."""

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    source = models.CharField(max_length=100, blank=True)
    date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Income {self.amount} from {self.source or 'unknown'}"


class MoneyToGet(models.Model):
    """Money other people owe the user (right sidebar 'Money To Get' list)."""

    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Money to get"
        verbose_name_plural = "Money to get"
        ordering = ["-amount"]

    def __str__(self):
        return f"{self.name} owes {self.amount}"


class MoneyToPay(models.Model):
    """Money the user owes other people (left sidebar 'Money To Pay' list)."""

    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Money to pay"
        verbose_name_plural = "Money to pay"
        ordering = ["-amount"]

    def __str__(self):
        return f"Owe {self.name} {self.amount}"


class NepalSavingsTransaction(models.Model):
    """Entry in the Nepal Savings transaction history (savings added / money used)."""

    ADDED = "added"
    USED = "used"
    TRANSACTION_TYPES = [
        (ADDED, "Savings Added"),
        (USED, "Money Used"),
    ]

    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    date = models.DateField()

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_type_display()}: {self.amount} on {self.date}"


class PortfolioHolding(models.Model):
    """A NEPSE stock position tracked on the stock exchange 'My Portfolio' sidebar."""

    symbol = models.CharField(max_length=20)
    company_name = models.CharField(max_length=150, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    buy_price = models.DecimalField(max_digits=12, decimal_places=2)
    buy_date = models.DateField(default=date.today)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.symbol} x{self.quantity} @ {self.buy_price}"


class FamilyMember(models.Model):
    """A family member with their own stock portfolio accordion on the stock exchange page."""

    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FamilyPortfolioHolding(models.Model):
    """A NEPSE stock position tracked under a specific family member's portfolio accordion.

    No buy price/date is stored - value is always just quantity x live market price.
    """

    family_member = models.ForeignKey(FamilyMember, on_delete=models.CASCADE, related_name="holdings")
    symbol = models.CharField(max_length=20)
    company_name = models.CharField(max_length=150, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.family_member.name}: {self.symbol} x{self.quantity}"


class AlertRecipient(models.Model):
    """A named person + WhatsApp number a price alert can be sent to (e.g. 'Ashmita')."""

    name = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class PriceAlert(models.Model):
    """A watch on a NEPSE symbol that fires once the price crosses a target, up or down."""

    UP = "up"
    DOWN = "down"
    DIRECTION_CHOICES = [
        (UP, "Crossed above"),
        (DOWN, "Dropped below"),
    ]

    BUY = "buy"
    SELL = "sell"
    ACTION_CHOICES = [
        (BUY, "Buy"),
        (SELL, "Sell"),
    ]

    symbol = models.CharField(max_length=20)
    company_name = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=4, choices=ACTION_CHOICES, default=BUY)
    target_price = models.DecimalField(max_digits=12, decimal_places=2)
    last_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    recipient = models.ForeignKey(
        AlertRecipient, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts"
    )
    holder = models.ForeignKey(
        FamilyMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="price_alerts",
        help_text="Which family member's share this alert is about (purely informational - doesn't change who gets notified).",
    )
    is_triggered = models.BooleanField(default=False)
    triggered_direction = models.CharField(max_length=4, choices=DIRECTION_CHOICES, blank=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    message_sent = models.BooleanField(
        default=False, help_text="Whether the WhatsApp alert message was actually delivered."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_triggered", "-created_at"]

    def __str__(self):
        return f"{self.symbol} @ Rs {self.target_price}"
