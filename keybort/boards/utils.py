import json

from django.http import HttpResponse

from . import const


def model_to_dict_verbose(instance, fields=None, exclude=None):
    data = {}
    for f in instance._meta.concrete_fields:
        if not f.editable:
            continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue

        value = f.value_from_object(instance)
        if f.choices:
            labels = dict(f.choices)
            if value not in labels:
                continue
            value = labels[value]

        data[f.verbose_name.capitalize()] = value
    return data


def keyboard_params(request):
    """(keyboard id, stock) from ?id=&stock= on keyboard urls, or None when they're missing/malformed"""
    kb_id = request.GET.get('id', '')
    stock = request.GET.get('stock')
    if not kb_id.isdigit() or stock not in ('0', '1'):
        return None
    return kb_id, stock == '1'


def bulk_ids(request):
    values = request.POST.getlist('ids') or request.GET.getlist('ids')
    return [value for value in values if value]


def htmx_swap(response, target, swap, trigger=None):
    """send an htmx response somewhere other than the requesting element's target"""
    response['HX-Retarget'] = target
    response['HX-Reswap'] = swap
    if trigger:
        response['HX-Trigger'] = trigger
    return response


def bulk_deleted(row_ids):
    triggers = {const.CLOSE_DIALOG_EVENT: '', 'rows-deleted': {'ids': row_ids}}
    return htmx_swap(HttpResponse(), '#page-dialog', 'none', json.dumps(triggers))
