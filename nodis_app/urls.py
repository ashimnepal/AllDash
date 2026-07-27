from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('league/', views.league, name='leaguepage'),
    path('motogp/', views.motogp, name='motogppage'),
    path('formula1/', views.formula1, name='formula1page'),
    path('expense_tracking/', views.expensetracking, name='expensetrackingpage'),
]