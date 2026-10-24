import csv
import io

from django import forms
from django.db import transaction
from django.db.models import Q

from . import const
from .managers import KeyboardManager

TRUE_VALUES = {'1', 'true', 't', 'yes', 'y', 'x'}
FALSE_VALUES = {'', '0', 'false', 'f', 'no', 'n'}


def part_type_aliases():
    aliases = {}
    for part_type in KeyboardManager.STOCK_FORMS:
        for alias in (
            part_type,
            const.PART_SINGULARS[part_type],
            const.PART_PLURALS[part_type],
        ):
            aliases[alias.lower()] = part_type
    return aliases


def stock_csv_columns():
    columns = ['type']
    for form_class in KeyboardManager.STOCK_FORMS.values():
        for name in form_class.base_fields:
            if name not in columns:
                columns.append(name)
    return columns


def stock_csv_template():
    out = io.StringIO()
    csv.writer(out).writerow(stock_csv_columns())
    return out.getvalue()


# return value, error
def normalize_value(field, raw):
    value = raw.strip()
    if isinstance(field, forms.BooleanField):
        if value.lower() in TRUE_VALUES:
            return 'on', None
        if value.lower() in FALSE_VALUES:
            return None, None
        return None, f'"{raw}" isn\'t a yes/no value'
    if isinstance(field, forms.TypedChoiceField) and value:
        for key, label in field.choices:
            if value.lower() in (str(key).lower(), str(label).lower()):
                return key, None
    return value, None


def read_rows(file):
    content = file.read()
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))
    headers = [(h or '').strip().lower() for h in reader.fieldnames or []]
    reader.fieldnames = headers
    return headers, reader


# return part type, form class, and errors for a row
def validate_row(line, row, aliases):
    errors = []
    part_type = aliases.get((row.get('type') or '').strip().lower())
    if part_type is None:
        return None, None, [(line, f'unknown type "{row.get("type") or ""}"')]

    form_class = KeyboardManager.STOCK_FORMS[part_type]
    data = {}
    for name, raw in row.items():
        if name in ('', 'type') or raw is None:
            continue
        field = form_class.base_fields.get(name)
        if field is None:
            if raw.strip():
                errors.append((line, f"{name} doesn't apply to {part_type}"))
            continue
        value, error = normalize_value(field, raw)
        if error:
            errors.append((line, f'{name}: {error}'))
        elif value:
            data[name] = value

    # fill a Django form with the data from the row and use those validators
    form = form_class(data)
    if not form.is_valid():
        for name, messages in form.errors.items():
            errors.extend((line, f'{name}: {message}') for message in messages)
    return part_type, form, errors


def matching_fields(model, fields):
    q = Q()
    for name, value in fields.items():
        if value in (None, '') and model._meta.get_field(name).empty_strings_allowed:
            q &= Q(**{f'{name}__isnull': True}) | Q(**{name: ''})
        else:
            q &= Q(**{name: value})
    return q


def handle_canned_parts_upload(file):
    result = {
        'created': dict.fromkeys(KeyboardManager.STOCK_FORMS, 0),
        'skipped': 0,
        'errors': [],
    }
    try:
        headers, reader = read_rows(file)
    except UnicodeDecodeError:
        result['errors'].append((0, 'file must be UTF-8 encoded CSV'))
        return result

    columns = stock_csv_columns()
    unknown = [h for h in headers if h and h not in columns]
    if 'type' not in headers:
        result['errors'].append((1, 'missing a type column'))
    if unknown:
        result['errors'].append((1, f'unknown columns: {", ".join(unknown)}'))
    if result['errors']:
        return result

    aliases = part_type_aliases()
    valid = []
    for line, row in enumerate(reader, start=2):
        if None in row:
            result['errors'].append((line, 'more values than columns'))
            continue
        if not any((value or '').strip() for value in row.values()):
            continue
        part_type, form, errors = validate_row(line, row, aliases)
        result['errors'].extend(errors)
        if not errors:
            valid.append((part_type, form))

    if result['errors']:
        return result

    # loop through the forms read out of the csv
    # and save any that are actually new
    seen = set()
    with transaction.atomic():
        for part_type, form in valid:
            _, custom_model, stock_model, _ = KeyboardManager.PART_MODELS[part_type]
            fields = KeyboardManager.part_fields(form.instance, custom_model)
            key = (
                part_type,
                tuple(sorted((k, None if v == '' else v) for k, v in fields.items())),
            )
            if (
                key in seen
                or stock_model.objects.filter(
                    matching_fields(stock_model, fields)
                ).exists()
            ):
                result['skipped'] += 1
                continue
            seen.add(key)
            form.save()
            result['created'][part_type] += 1
    return result
