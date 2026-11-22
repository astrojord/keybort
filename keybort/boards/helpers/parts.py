from typing import NamedTuple

from .. import const
from ..forms import (
    CustomKeycapsForm,
    CustomKitForm,
    CustomPlateForm,
    CustomStabilizerForm,
    CustomSwitchForm,
    StockKeycapsForm,
    StockKitForm,
    StockPlateForm,
    StockStabilizerForm,
    StockSwitchForm,
)
from ..models import (
    CustomKeycaps,
    CustomKit,
    CustomPlate,
    CustomStabilizer,
    CustomSwitch,
    Keycaps,
    Kit,
    Plate,
    Stabilizer,
    StockKeycaps,
    StockKit,
    StockPlate,
    StockStabilizer,
    StockSwitch,
    Switch,
)


class PartModels(NamedTuple):
    wrapper: type
    custom: type
    stock: type
    form: type
    stock_form: type


PART_MODELS: dict[str, PartModels] = {
    'kit': PartModels(Kit, CustomKit, StockKit, CustomKitForm, StockKitForm),
    'switch': PartModels(
        Switch, CustomSwitch, StockSwitch, CustomSwitchForm, StockSwitchForm
    ),
    'keycaps': PartModels(
        Keycaps, CustomKeycaps, StockKeycaps, CustomKeycapsForm, StockKeycapsForm
    ),
    'plate': PartModels(
        Plate, CustomPlate, StockPlate, CustomPlateForm, StockPlateForm
    ),
    'stabilizer': PartModels(
        Stabilizer,
        CustomStabilizer,
        StockStabilizer,
        CustomStabilizerForm,
        StockStabilizerForm,
    ),
}


def part_obj(part):
    # custom keyboards point at wrappers (Kit, Switch, ...), stock keyboards point straight at Stock* parts
    return part.obj if hasattr(part, 'obj') else part


def part_type_of(inv):
    return next(
        part_type for part_type in PART_MODELS if getattr(inv, f'{part_type}_id')
    )


def part_fields(obj, custom_model):
    return {
        field.attname: getattr(obj, field.attname)
        for field in custom_model._meta.concrete_fields
        if not field.primary_key
    }


def part_in_use(wrapper, ignore=None):
    if wrapper is None:
        return False
    for rel in wrapper._meta.related_objects:
        qs = rel.related_model._base_manager.filter(**{rel.field.name: wrapper})
        if isinstance(ignore, rel.related_model):
            qs = qs.exclude(pk=ignore.pk)
        if qs.exists():
            return True
    return False


def board_switch_count(kb, fallback=1):
    """switches on a board: what it recorded, else one per key on its kit"""
    count = kb.switch_count
    if not count and kb.kit:
        count = part_obj(kb.kit).total_keys
    return count or fallback


def board_quantity(kb, part_type):
    return board_switch_count(kb) if part_type == 'switch' else 1


def switch_kind(obj):
    """{slug, label} for a switch's category dot, or None"""
    if not obj or not obj.category:
        return None
    return {
        'slug': const.SWITCH_KINDS[obj.category],
        'label': obj.get_category_display(),
    }
