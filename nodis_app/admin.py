from django.contrib import admin

from .models import (
    Budget,
    Category,
    Expense,
    Income,
    MoneyToGet,
    MoneyToPay,
    NepalSavingsTransaction,
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
