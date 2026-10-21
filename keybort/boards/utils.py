def model_to_dict_verbose(instance, fields=None, exclude=None):
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields:
        if not getattr(f, 'editable', False):
            continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue

        value = f.value_from_object(instance)
        if f.choices:
            try:
                value = next(display for db, display in f.choices if value == db)
            except StopIteration:
                continue

        data[f.verbose_name.capitalize()] = value
    return data


def keyboard_params(request):
    """(keyboard id, stock) from ?id=&stock= on keyboard urls, or None when they're missing/malformed"""
    kb_id = request.GET.get('id', '')
    stock = request.GET.get('stock')
    if not kb_id.isdigit() or stock not in ('0', '1'):
        return None
    return kb_id, stock == '1'


def htmx_swap(response, target, swap, trigger=None):
    """send an htmx response somewhere other than the requesting element's target"""
    response['HX-Retarget'] = target
    response['HX-Reswap'] = swap
    if trigger:
        response['HX-Trigger'] = trigger
    return response
