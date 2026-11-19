from django.core.exceptions import BadRequest

from . import const


def is_id(value):
    return value.isdecimal() and len(value) <= const.MAX_ID_DIGITS


def require_id(request, name='id'):
    value = request.GET.get(name, '')
    if not is_id(value):
        raise BadRequest
    return value


def require_stock_flag(request):
    stock = request.GET.get('stock')
    if stock not in ('0', '1'):
        raise BadRequest
    return stock == '1'


def keyboard_params(request):
    """(keyboard id, stock) from ?id=&stock= on keyboard urls"""
    return require_id(request), require_stock_flag(request)


def bulk_ids(request):
    values = request.POST.getlist('ids') or request.GET.getlist('ids')
    return [value for value in values if value]
