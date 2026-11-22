import csv
import dataclasses
import io
from typing import NamedTuple

from django import forms
from django.db import transaction
from django.db.models import Q

from .helpers.parts import PART_TYPES, part_fields

TRUE_VALUES = {'1', 'true', 't', 'yes', 'y', 'x'}
FALSE_VALUES = {'', '0', 'false', 'f', 'no', 'n'}

type RowError = tuple[int, str]


class RowResult(NamedTuple):
    part_type: str | None
    form: forms.ModelForm | None
    errors: list[RowError]


@dataclasses.dataclass
class UploadResult:
    created: dict[str, int] = dataclasses.field(
        default_factory=lambda: dict.fromkeys(PART_TYPES, 0)
    )
    skipped: int = 0
    errors: list[RowError] = dataclasses.field(default_factory=list)


def part_type_aliases():
    aliases = {}
    for part_type, spec in PART_TYPES.items():
        for alias in (part_type, spec.singular, spec.plural):
            aliases[alias.lower()] = part_type
    return aliases


def stock_csv_columns():
    columns = ['type']
    for spec in PART_TYPES.values():
        for name in spec.stock_form.base_fields:
            if name not in columns:
                columns.append(name)
    return columns


def stock_csv_template():
    out = io.StringIO()
    csv.writer(out).writerow(stock_csv_columns())
    return out.getvalue()


def normalize_value(field, raw) -> tuple[str | None, str | None]:
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


def validate_row(line, row, aliases) -> RowResult:
    errors = []
    part_type = aliases.get((row.get('type') or '').strip().lower())
    if part_type is None:
        return RowResult(
            None, None, [(line, f'unknown type "{row.get("type") or ""}"')]
        )

    form_class = PART_TYPES[part_type].stock_form
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

    form = form_class(data)
    if not form.is_valid():
        for name, messages in form.errors.items():
            errors.extend((line, f'{name}: {message}') for message in messages)
    return RowResult(part_type, form, errors)


def blanks_as_none(fields):
    # a blank CSV cell and an unset field both mean "not set", so compare them as None
    return {name: None if value == '' else value for name, value in fields.items()}


def matching_fields(model, fields):
    q = Q()
    for name, value in blanks_as_none(fields).items():
        if value is None and model._meta.get_field(name).empty_strings_allowed:
            q &= Q(**{f'{name}__isnull': True}) | Q(**{name: ''})
        else:
            q &= Q(**{name: value})
    return q


def handle_canned_parts_upload(file) -> UploadResult:
    result = UploadResult()
    try:
        headers, reader = read_rows(file)
    except UnicodeDecodeError:
        result.errors.append((0, 'file must be UTF-8 encoded CSV'))
        return result

    columns = stock_csv_columns()
    unknown = [h for h in headers if h and h not in columns]
    if 'type' not in headers:
        result.errors.append((1, 'missing a type column'))
    if unknown:
        result.errors.append((1, f'unknown columns: {", ".join(unknown)}'))
    if result.errors:
        return result

    aliases = part_type_aliases()
    valid = []
    for line, row in enumerate(reader, start=2):
        if None in row:
            result.errors.append((line, 'more values than columns'))
            continue
        if not any((value or '').strip() for value in row.values()):
            continue
        part_type, form, errors = validate_row(line, row, aliases)
        result.errors.extend(errors)
        if not errors:
            valid.append((part_type, form))

    if result.errors:
        return result

    seen = set()
    with transaction.atomic():
        for part_type, form in valid:
            spec = PART_TYPES[part_type]
            fields = part_fields(form.instance, spec.custom)
            key = (part_type, tuple(sorted(blanks_as_none(fields).items())))
            if (
                key in seen
                or spec.stock.objects.filter(
                    matching_fields(spec.stock, fields)
                ).exists()
            ):
                result.skipped += 1
                continue
            seen.add(key)
            form.save()
            result.created[part_type] += 1
    return result
