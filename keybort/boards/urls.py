from django.urls import path

from . import views
from .helpers.parts import PART_TYPES

urlpatterns = [
    path('', views.index, name='index'),
    path('stats', views.stats, name='stats'),
    path('typing/results', views.save_typing_result, name='typing_result_save'),
    path('inventory/', views.inventory_keyboards),
    path('inventory/keyboards', views.inventory_keyboards, name='inventory_keyboards'),
    path('inventory/keyboards/edit', views.edit_keyboard, name='keyboard_edit'),
    path('inventory/keyboards/add', views.add_keyboard, name='keyboard_add'),
    path('inventory/keyboards/delete', views.delete_keyboards, name='keyboard_delete'),
    path('inventory/parts', views.inventory_parts, name='inventory_parts'),
    path('inventory/parts/add', views.add_part, name='part_add'),
    path('inventory/parts/edit', views.edit_part, name='part_edit'),
    path('inventory/parts/delete', views.delete_parts, name='part_delete'),
    path('inventory/parts/quantity', views.part_quantity, name='part_quantity'),
    path('inventory/parts/promote', views.promote_part, name='part_promote'),
    path('account', views.account, name='account'),
    path('stock/prebuilts', views.stock_prebuilts, name='stock_prebuilts'),
    path('stock/prebuilts/add', views.add_stock_prebuilt, name='stock_prebuilt_add'),
    path('stock/prebuilts/edit', views.edit_stock_prebuilt, name='stock_prebuilt_edit'),
    path(
        'stock/prebuilts/delete',
        views.delete_stock_prebuilts,
        name='stock_prebuilt_delete',
    ),
    path(
        'stock/prebuilts/to-inventory',
        views.collect_stock_prebuilt,
        name='stock_prebuilt_collect',
    ),
    path('stock/parts/add', views.add_stock_part, name='stock_part_add'),
    path('stock/parts/upload', views.upload_stock_parts, name='stock_part_upload'),
    path(
        'stock/parts/upload/template',
        views.stock_upload_template,
        name='stock_upload_template',
    ),
    path('stock/parts/edit', views.edit_stock_part, name='stock_part_edit'),
    path('stock/parts/delete', views.delete_stock_parts, name='stock_part_delete'),
    path(
        'stock/parts/to-inventory',
        views.collect_stock_part,
        name='stock_part_collect',
    ),
    path('get_part_detail', views.part_detail, name='part_detail'),
]

# one catalog page per part type
urlpatterns += [
    path(
        f'stock/{spec.slug}',
        views.stock_parts,
        {'part_type': part_type},
        name=spec.catalog_url_name,
    )
    for part_type, spec in PART_TYPES.items()
]
