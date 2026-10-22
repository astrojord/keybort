from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('inventory/', views.inventory_keyboards, name='inventory_keyboards'),
    path('inventory/keyboards', views.inventory_keyboards, name='inventory_keyboards'),
    path('inventory/keyboards/edit', views.edit_keyboard, name='keyboard_edit'),
    path('inventory/keyboards/add', views.add_keyboard, name='keyboard_add'),
    path('inventory/keyboards/delete', views.delete_keyboard, name='keyboard_delete'),
    path('inventory/parts', views.inventory_parts, name='inventory_parts'),
    path('inventory/parts/add', views.add_part, name='part_add'),
    path('inventory/parts/edit', views.edit_part, name='part_edit'),
    path('inventory/parts/delete', views.delete_part, name='part_delete'),
    path('account', views.account, name='account'),
    path('stock/', views.search_stock, name='search_stock'),
    path('stock/prebuilts', views.stock_prebuilts, name='stock_prebuilts'),
    path('stock/kits', views.stock_kits, name='stock_kits'),
    path('stock/keycaps', views.stock_keycaps, name='stock_keycaps'),
    path('stock/switches', views.stock_switches, name='stock_switches'),
    path('stock/plates', views.stock_plates, name='stock_plates'),
    path('stock/stabilizers', views.stock_stabilizers, name='stock_stabilizers'),
    path('get_part_detail', views.part_detail, name='part_detail'),
]
