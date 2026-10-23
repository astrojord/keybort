from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('inventory/', views.inventory_keyboards, name='inventory_keyboards'),
    path('inventory/keyboards', views.inventory_keyboards, name='inventory_keyboards'),
    path('inventory/keyboards/edit', views.edit_keyboard, name='keyboard_edit'),
    path('inventory/keyboards/add', views.add_keyboard, name='keyboard_add'),
    path('inventory/keyboards/delete', views.delete_keyboards, name='keyboard_delete'),
    path('inventory/parts', views.inventory_parts, name='inventory_parts'),
    path('inventory/parts/add', views.add_part, name='part_add'),
    path('inventory/parts/edit', views.edit_part, name='part_edit'),
    path('inventory/parts/delete', views.delete_parts, name='part_delete'),
    path('inventory/parts/quantity', views.part_quantity, name='part_quantity'),
    path('account', views.account, name='account'),
    path('stock/', views.search_stock, name='search_stock'),
    path('stock/prebuilts', views.stock_prebuilts, name='stock_prebuilts'),
    path('stock/prebuilts/add', views.add_stock_prebuilt, name='stock_prebuilt_add'),
    path('stock/prebuilts/edit', views.edit_stock_prebuilt, name='stock_prebuilt_edit'),
    path(
        'stock/prebuilts/delete',
        views.delete_stock_prebuilts,
        name='stock_prebuilt_delete',
    ),
    path(
        'stock/prebuilts/collect',
        views.collect_stock_prebuilt,
        name='stock_prebuilt_collect',
    ),
    path('stock/kits', views.stock_kits, name='stock_kits'),
    path('stock/keycaps', views.stock_keycaps, name='stock_keycaps'),
    path('stock/switches', views.stock_switches, name='stock_switches'),
    path('stock/plates', views.stock_plates, name='stock_plates'),
    path('stock/stabilizers', views.stock_stabilizers, name='stock_stabilizers'),
    path('stock/parts/add', views.add_stock_part, name='stock_part_add'),
    path('stock/parts/edit', views.edit_stock_part, name='stock_part_edit'),
    path('stock/parts/delete', views.delete_stock_parts, name='stock_part_delete'),
    path('stock/parts/collect', views.collect_stock_part, name='stock_part_collect'),
    path('get_part_detail', views.part_detail, name='part_detail'),
]
