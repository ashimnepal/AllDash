from django.contrib import admin

from .models import (
    AlertRecipient,
    Budget,
    Category,
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


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("month", "amount")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "amount", "date")
    list_filter = ("category", "date")
    search_fields = ("name",)


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("source", "amount", "date")


@admin.register(MoneyToGet)
class MoneyToGetAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "updated_at")


@admin.register(MoneyToPay)
class MoneyToPayAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "updated_at")


@admin.register(NepalSavingsTransaction)
class NepalSavingsTransactionAdmin(admin.ModelAdmin):
    list_display = ("type", "amount", "note", "date")
    list_filter = ("type", "date")


@admin.register(PortfolioHolding)
class PortfolioHoldingAdmin(admin.ModelAdmin):
    list_display = ("symbol", "company_name", "quantity", "buy_price", "buy_date")
    list_filter = ("buy_date",)
    search_fields = ("symbol", "company_name")


@admin.register(AlertRecipient)
class AlertRecipientAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "created_at")
    search_fields = ("name", "phone_number")


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ("symbol", "action", "target_price", "recipient", "is_triggered", "triggered_direction", "triggered_at")
    list_filter = ("action", "is_triggered")
    search_fields = ("symbol", "company_name")


@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(FamilyPortfolioHolding)
class FamilyPortfolioHoldingAdmin(admin.ModelAdmin):
    list_display = ("family_member", "symbol", "company_name", "quantity", "buy_price", "buy_date")
    list_filter = ("family_member", "buy_date")
    search_fields = ("symbol", "company_name")
