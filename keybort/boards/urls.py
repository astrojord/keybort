from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('inventory/keyboards', views.inventory_keyboards, name='inventory_keyboards'),
    path('inventory/parts', views.inventory_parts, name='inventory_parts'),
]