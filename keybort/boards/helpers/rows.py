from dataclasses import dataclass
from urllib.parse import urlencode

from django.urls import reverse

from .. import const
from ..models import (
    part_name,
)
from ..request_params import is_id
from .parts import (
    PART_TYPES,
    part_obj,
    part_type_of,
    switch_kind,
)


def keyboard_ref(kb):
    return f'{"stock" if kb.is_stock else "custom"}-{kb.pk}'


def parse_keyboard_ref(ref):
    kind, _, kb_id = ref.partition('-')
    if kind not in ('stock', 'custom') or not is_id(kb_id):
        return None
    return kb_id, kind == 'stock'


def keyboard_row_id(kb):
    return f'keyboard-{keyboard_ref(kb)}'


def part_row_id(inv):
    return f'part-{inv.pk}'


def stock_part_row_id(part_type, obj):
    return f'stock-{part_type}-{obj.pk}'


def prebuilt_row_id(kb):
    return f'prebuilt-{kb.pk}'


def detail_params(part_type, obj, edit_url):
    return urlencode(
        {'type': part_type, 'id': obj.pk, 'stock': int(obj.is_stock), 'edit': edit_url}
    )


def filter_facets(rows, selected, specs):
    facets = []
    for key, label, fixed in specs:
        values = fixed or sorted(
            {value for row in rows for value in row.facets.get(key, [])},
            key=str.lower,
        )
        chosen = selected.getlist(key)
        facets.append(
            {
                'key': key,
                'label': label,
                'options': [(value, value in chosen) for value in values],
            }
        )
    return facets


def field_label(model, name):
    if name in const.FIELD_LABELS:
        return const.FIELD_LABELS[name]
    return model._meta.get_field(name).verbose_name.capitalize()


def field_display(obj, name):
    if name in const.COMBINED_FIELDS:
        values = [field_display(obj, part) for part in const.COMBINED_FIELDS[name]]
        return ' / '.join(value or '—' for value in values) if any(values) else ''
    field = obj._meta.get_field(name)
    value = getattr(obj, name)
    if value is None or value == '':
        return ''
    if field.choices:
        return getattr(obj, f'get_{name}_display')()
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, float):
        return f'{value:g}{field.help_text}'
    return str(value)


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


def field_cell(obj, name):
    return {
        'value': field_display(obj, name),
        'flag': getattr(obj, name) if name in const.ICON_FIELDS else None,
        'switch_kind': switch_kind(obj) if name == 'category' else None,
    }


def part_info(part_type, obj):
    match part_type:
        case 'kit':
            info = [
                obj.size,
                obj.layout,
                obj.case_material,
                obj.mount_type,
                obj.pcb and f'{obj.pcb} PCB',
            ]
        case 'switch':
            info = [
                obj.get_category_display() if obj.category else None,
                obj.bottom_out_force and f'{obj.bottom_out_force:g}gf',
                obj.top_housing and f'{obj.get_top_housing_display()} top',
                obj.bottom_housing and f'{obj.get_bottom_housing_display()} bottom',
                obj.lubed and 'lubed',
                obj.filmed and 'filmed',
            ]
        case 'keycaps':
            info = [obj.material]
        case _:
            info = []
    return ', '.join(str(item) for item in [*info, obj.notes] if item)


def part_columns():
    return [
        {
            'type': part_type,
            'key': f'{part_type}-{name}',
            'label': field_label(spec.custom, name),
        }
        for part_type, spec in PART_TYPES.items()
        for name in spec.inventory_columns
    ]


def part_cells(part_type, obj):
    blank = {'value': '', 'flag': None}
    return [
        {
            'type': column_type,
            **(field_cell(obj, name) if column_type == part_type else blank),
        }
        for column_type, spec in PART_TYPES.items()
        for name in spec.inventory_columns
    ]


@dataclass(frozen=True)
class PartRef:
    name: str
    detail_params: str
    switch_kind: dict | None = None


def part_ref(part_type, part, edit_url):
    if part is None:
        return None
    obj = part_obj(part)
    return PartRef(
        name=part_name(obj),
        detail_params=detail_params(part_type, obj, edit_url),
        switch_kind=switch_kind(obj) if part_type == 'switch' else None,
    )


@dataclass(frozen=True)
class PartRow:
    id: int
    row_id: str
    type: str
    type_label: str
    name: str
    is_stock: bool
    quantity: int
    info: str
    cells: list[dict]
    switch_kind: dict | None
    detail_params: str


def part_row(inv):
    part_type = part_type_of(inv)
    obj = getattr(inv, part_type).obj
    return PartRow(
        id=inv.pk,
        row_id=part_row_id(inv),
        type=part_type,
        type_label=PART_TYPES[part_type].singular,
        name=part_name(obj),
        is_stock=obj.is_stock,
        quantity=inv.quantity,
        info=part_info(part_type, obj),
        cells=part_cells(part_type, obj),
        switch_kind=switch_kind(obj) if part_type == 'switch' else None,
        detail_params=detail_params(
            part_type, obj, f'{reverse("part_edit")}?id={inv.pk}'
        ),
    )


@dataclass(frozen=True)
class KeyboardRow:
    id: int
    row_id: str
    ref: str
    url_params: str
    is_stock: bool
    notes: str | None
    kit: PartRef | None
    pcb: str | None
    switch: PartRef | None
    switch_count: int | None
    keycaps: PartRef | None
    plate: PartRef | None
    stabilizer: PartRef | None


def keyboard_row(kb):
    url_params = f'id={kb.pk}&stock={int(kb.is_stock)}'
    edit_url = f'{reverse("keyboard_edit")}?{url_params}&step='
    refs = {
        part_type: part_ref(part_type, getattr(kb, part_type), f'{edit_url}{part_type}')
        for part_type in PART_TYPES
    }
    return KeyboardRow(
        id=kb.pk,
        row_id=keyboard_row_id(kb),
        ref=keyboard_ref(kb),
        url_params=url_params,
        is_stock=kb.is_stock,
        notes=kb.notes,
        pcb=part_obj(kb.kit).pcb if kb.kit else None,
        switch_count=kb.switch_count if kb.switch else None,
        **refs,
    )


def stock_part_specs(part_type):
    spec = PART_TYPES[part_type]
    columns = [(name, field_label(spec.stock, name)) for name in spec.stock_columns]
    facets = [(name, field_label(spec.stock, name), None) for name in spec.stock_facets]
    return columns, facets


@dataclass(frozen=True)
class StockPartRow:
    id: int
    row_id: str
    type: str
    url_params: str
    name: str
    detail_params: str
    columns: list[dict]
    facets: dict[str, list[str]]
    notes: str | None
    quantity: int
    switch_kind: dict | None


def stock_part_row(part_type, obj, quantity=0):
    spec = PART_TYPES[part_type]
    facets = {}
    for name in spec.stock_facets:
        value = field_display(obj, name)
        if value:
            facets[name] = [value]
    return StockPartRow(
        id=obj.pk,
        row_id=stock_part_row_id(part_type, obj),
        type=part_type,
        url_params=f'type={part_type}&id={obj.pk}',
        name=part_name(obj),
        detail_params=detail_params(part_type, obj, ''),
        columns=[field_cell(obj, name) for name in spec.stock_columns],
        facets=facets,
        notes=obj.notes,
        quantity=quantity,
        switch_kind=switch_kind(obj) if part_type == 'switch' else None,
    )


@dataclass(frozen=True)
class PrebuiltRow:
    id: int
    row_id: str
    name: str
    owned: bool
    connectivity: str
    facets: dict[str, list[str]]
    notes: str | None
    size: str | None
    layout: str | None
    kit: PartRef | None
    switch: PartRef | None
    keycaps: PartRef | None
    plate: PartRef | None
    stabilizer: PartRef | None


def stock_prebuilt_row(kb, owned=False):
    connectivity = [
        label
        for label, enabled in (
            (const.WIRELESS, kb.wireless),
            (const.BLUETOOTH, kb.bluetooth),
        )
        if enabled
    ] or [const.WIRED]
    facets = {'connectivity': connectivity}
    if kb.kit:
        for key in ('brand', 'size', 'layout'):
            if getattr(kb.kit, key):
                facets[key] = [getattr(kb.kit, key)]
    return PrebuiltRow(
        id=kb.pk,
        row_id=prebuilt_row_id(kb),
        name=str(kb),
        owned=owned,
        connectivity=', '.join(connectivity),
        facets=facets,
        notes=kb.notes,
        size=kb.kit.size if kb.kit else None,
        layout=kb.kit.layout if kb.kit else None,
        **{
            part_type: part_ref(part_type, getattr(kb, part_type), '')
            for part_type in PART_TYPES
        },
    )
