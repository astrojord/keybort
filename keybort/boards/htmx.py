import json

from django.http import HttpResponse

from . import const


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
