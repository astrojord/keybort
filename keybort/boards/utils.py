def model_to_dict_verbose(instance, fields=None, exclude=None):
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields:
        if not getattr(f, "editable", False):
            continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue

        value = f.value_from_object(instance)
        if f.choices:
            value = [display for db, display in f.choices if value == db][0]
            
        data[f.verbose_name.capitalize()] = value
    return data