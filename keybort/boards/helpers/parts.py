from dataclasses import dataclass

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
    CustomOrStock,
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


@dataclass(frozen=True)
class PartType:
    singular: str
    plural: str
    step_label: str  # heading for this step in the keyboard/part edit modals
    slug: str  # path segment
    wrapper: type
    custom: type
    stock: type
    form: type
    stock_form: type
    inventory_columns: list[str]
    stock_columns: list[str]
    stock_facets: list[str]

    @property
    def catalog_url_name(self):
        return f'stock_{self.slug}'


PART_TYPES = {
    'kit': PartType(
        singular='Kit',
        plural='Kits',
        step_label='Kit',
        slug='kits',
        wrapper=Kit,
        custom=CustomKit,
        stock=StockKit,
        form=CustomKitForm,
        stock_form=StockKitForm,
        inventory_columns=[
            'size',
            'layout',
            'pcb',
            'case_material',
            'mount_type',
            'notes',
        ],
        stock_columns=['size', 'layout', 'pcb', 'case_material', 'mount_type'],
        stock_facets=['brand', 'size', 'layout', 'mount_type'],
    ),
    'switch': PartType(
        singular='Switch',
        plural='Switches',
        step_label='Switches',
        slug='switches',
        wrapper=Switch,
        custom=CustomSwitch,
        stock=StockSwitch,
        form=CustomSwitchForm,
        stock_form=StockSwitchForm,
        inventory_columns=[
            'category',
            'stem',
            'force',
            'travel_distance',
            'housing',
            'lubed',
            'filmed',
            'notes',
        ],
        stock_columns=['category', 'stem', 'force', 'travel_distance', 'housing'],
        stock_facets=['brand', 'category', 'stem', 'top_housing', 'bottom_housing'],
    ),
    'keycaps': PartType(
        singular='Keycaps',
        plural='Keycaps',
        step_label='Keycaps',
        slug='keycaps',
        wrapper=Keycaps,
        custom=CustomKeycaps,
        stock=StockKeycaps,
        form=CustomKeycapsForm,
        stock_form=StockKeycapsForm,
        inventory_columns=['material', 'notes'],
        stock_columns=['material'],
        stock_facets=['brand', 'material'],
    ),
    'plate': PartType(
        singular='Plate',
        plural='Plates',
        step_label='Plate',
        slug='plates',
        wrapper=Plate,
        custom=CustomPlate,
        stock=StockPlate,
        form=CustomPlateForm,
        stock_form=StockPlateForm,
        inventory_columns=['material', 'flex_cuts', 'half', 'notes'],
        stock_columns=['material', 'flex_cuts', 'half'],
        stock_facets=['material', 'flex_cuts', 'half'],
    ),
    'stabilizer': PartType(
        singular='Stabilizer',
        plural='Stabilizers',
        step_label='Stabilizers',
        slug='stabilizers',
        wrapper=Stabilizer,
        custom=CustomStabilizer,
        stock=StockStabilizer,
        form=CustomStabilizerForm,
        stock_form=StockStabilizerForm,
        inventory_columns=['notes'],
        stock_columns=[],
        stock_facets=['brand'],
    ),
}


def part_obj(part):
    # custom keyboards point at wrappers (Kit, Switch, ...), stock keyboards point straight at Stock* parts
    return part.obj if isinstance(part, CustomOrStock) else part


def part_type_of(inv):
    return next(
        part_type for part_type in PART_TYPES if getattr(inv, f'{part_type}_id')
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
