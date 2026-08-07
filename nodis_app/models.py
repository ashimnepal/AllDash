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
