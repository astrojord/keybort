from . import const


def is_id(value):
    return value.isdecimal() and len(value) <= const.MAX_ID_DIGITS


def keyboard_params(request):
    """(keyboard id, stock) from ?id=&stock= on keyboard urls, or None when they're missing/malformed"""
    kb_id = request.GET.get('id', '')
    stock = request.GET.get('stock')
    if not is_id(kb_id) or stock not in ('0', '1'):
        return None
    return kb_id, stock == '1'


def bulk_ids(request):
    values = request.POST.getlist('ids') or request.GET.getlist('ids')
    return [value for value in values if value]
