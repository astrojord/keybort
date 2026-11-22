from dataclasses import dataclass

from django.db.models import QuerySet
from django.forms import ModelForm
from django.forms.models import model_to_dict

from .. import const
from ..forms import (
    CustomKeyboardDetailsForm,
    StockKeyboardDetailsForm,
)
from ..models import (
    CustomKeyboard,
    Inventory,
    StockKeyboard,
    part_name,
)
from ..request_params import is_id
from ..services.base import UserScoped
from ..services.inventory import PartService
from .parts import (
    PART_TYPES,
    board_switch_count,
    part_obj,
    part_type_of,
)


def parse_quantity(value):
    value = (value or '').strip()
    if not is_id(value):
        return None
    quantity = int(value)
    return quantity if 0 < quantity <= const.MAX_QUANTITY else None


@dataclass
class PartChoice:
    type: str
    label: str
    required: bool
    catalog: bool
    source: str
    stock_options: QuerySet
    stock_id: str
    owned_rows: QuerySet[Inventory] | None
    owned_options: list[dict] | None
    owned_id: str
    # stock + custom, plus "from my parts" and skip when they apply
    source_cards: int
    form: ModelForm
    current: dict | None
    removal: str
    # switch count, filled in by keyboard_form_context for the switch step
    count: int | str | None = None
    error: str | None = None

    def validate(self, data):
        match self.source:
            case 'stock':
                stock_id = data.get(f'{self.type}-stock', '')
                obj = (
                    self.stock_options.filter(pk=stock_id).first()
                    if is_id(stock_id)
                    else None
                )
                if obj is not None:
                    return ('stock', obj)
                self.error = f'Choose a stock option for {self.label.lower()}.'
            case 'custom':
                if self.form.is_valid():
                    return ('custom', self.form)
                self.error = 'Found some errors while checking the form.'
            case 'owned' if self.owned_rows is not None:
                row_id = data.get(f'{self.type}-owned', '')
                row = (
                    self.owned_rows.filter(pk=row_id).first() if is_id(row_id) else None
                )
                if row is not None:
                    return ('owned', row)
                self.error = f'Choose {self.label.lower()} from your parts.'
            case 'none' if not self.required:
                pass
            case _:
                self.error = (
                    f'Choose a stock {self.label.lower()} or enter a custom one.'
                )
        return None

    def validate_switch_count(self, data, choice):
        count = parse_quantity(data.get('switch-count'))
        source, value = choice
        if count is None:
            self.error = 'Enter how many switches are on the board.'
        elif source == 'owned' and count > value.quantity:
            self.error = f'You only have {value.quantity} of those switches.'
        return count


@dataclass
class KeyboardSubmission:
    details_form: ModelForm
    chosen: dict[str, tuple]
    removal: dict[str, str]
    switch_count: int | None = None
    step: str | None = None


class ModalForms(UserScoped):
    def keyboard_form_context(self, action_url, data=None, current=None, kind=None):
        data = data or {}
        parts = [
            self.part_choice(
                part_type,
                data,
                current=getattr(current, part_type, None),
                required=part_type == 'kit',
                owned=PartService(self.user).owned_parts(part_type),
                preferred=self.profile.default_part_source,
            )
            for part_type in PART_TYPES
        ]
        switch_default = (
            board_switch_count(current, fallback='')
            if current and current.switch
            else ''
        )
        parts[list(PART_TYPES).index('switch')].count = data.get(
            'switch-count', switch_default
        )

        if isinstance(current, CustomKeyboard):
            details_form = CustomKeyboardDetailsForm(
                data or None, prefix='details', instance=current
            )
        else:
            initial = (
                model_to_dict(current, fields=CustomKeyboardDetailsForm._meta.fields)
                if current
                else None
            )
            details_form = CustomKeyboardDetailsForm(
                data or None, prefix='details', initial=initial
            )

        prebuilt_options = [
            {'id': kb.pk, 'name': str(kb)}
            for kb in StockKeyboard.objects.select_related('kit')
        ]
        if kind == 'prebuilt' and not prebuilt_options:
            kind = None
        step = {'prebuilt': 'prebuilt', 'custom': parts[0].type}.get(kind)

        return {
            'action_url': action_url,
            'editing': current is not None,
            'from_prebuilt': current is not None and current.is_stock,
            'kind': data.get('kind', kind or 'custom'),
            'step': step,
            'prebuilt_options': prebuilt_options,
            'prebuilt_id': data.get('prebuilt', ''),
            'prebuilt_error': None,
            'parts': parts,
            'details_form': details_form,
        }

    def stock_keyboard_form_context(self, action_url, data=None, current=None):
        data = data or {}
        return {
            'action_url': action_url,
            'editing': current is not None,
            'parts': [
                self.part_choice(
                    part_type,
                    data,
                    current=getattr(current, part_type, None),
                    required=part_type == 'kit',
                    preferred='stock',
                    catalog=True,
                )
                for part_type in PART_TYPES
            ],
            'details_form': StockKeyboardDetailsForm(
                data or None, prefix='details', instance=current
            ),
            'step': None,
        }

    def add_part_context(self, data=None, part_type=None):
        data = data or {}
        return {
            'part_type': data.get('type', part_type or 'kit'),
            'parts': [
                self.part_choice(
                    t,
                    data,
                    required=True,
                    preferred=self.profile.default_part_source,
                )
                for t in PART_TYPES
            ],
            'quantity': data.get('quantity', '1'),
            'quantity_error': None,
            'step': part_type,
        }

    def edit_part_context(self, inv, action_url, data=None):
        part_type = part_type_of(inv)
        wrapper = getattr(inv, part_type)
        form = None
        if wrapper.custom_id:
            form = PART_TYPES[part_type].form(
                data, prefix=part_type, instance=wrapper.custom
            )
        return {
            'inv': inv,
            'name': part_name(wrapper.obj),
            'type_label': PART_TYPES[part_type].singular,
            'form': form,
            'quantity': data.get('quantity', '') if data else inv.quantity,
            'quantity_error': None,
            'action_url': action_url,
        }

    @classmethod
    def part_choice(
        cls,
        part_type,
        data,
        current=None,
        required=False,
        owned=None,
        preferred=const.DEFAULT_PART_SOURCE,
        catalog=False,
    ):
        spec = PART_TYPES[part_type]
        form_class = spec.stock_form if catalog else spec.form
        label = spec.step_label
        stock_options = spec.stock.objects.all()
        owned_options = None
        if owned is not None:
            owned_options = []
            for row in owned:
                obj = getattr(row, part_type).obj
                owned_options.append(
                    {
                        'id': row.pk,
                        'name': part_name(obj),
                        'is_stock': obj.is_stock,
                        'quantity': row.quantity,
                        'total_keys': getattr(obj, 'total_keys', None),
                    }
                )
        instance = None
        stock_id = ''
        if current is None:
            if not required:
                default_source = 'none'
            elif preferred == 'smart' and owned_options:
                default_source = 'owned'
            elif preferred != 'custom' and stock_options:
                default_source = 'stock'
            else:
                default_source = 'custom'
        elif isinstance(current, spec.stock):
            default_source, stock_id = 'stock', str(current.pk)
        elif current.stock_id:
            default_source, stock_id = 'stock', str(current.stock_id)
        else:
            default_source, instance = 'custom', current.custom

        source = data.get(f'{part_type}-source', default_source)
        return PartChoice(
            type=part_type,
            label=label,
            required=required,
            catalog=catalog,
            source=source,
            stock_options=stock_options,
            stock_id=data.get(f'{part_type}-stock', stock_id),
            owned_rows=owned,
            owned_options=owned_options,
            owned_id=data.get(f'{part_type}-owned', ''),
            source_cards=2 + (owned is not None) + (not required),
            form=form_class(
                (data or None) if source == 'custom' else None,
                prefix=part_type,
                instance=instance,
            ),
            current={
                'name': str(part_obj(current)),
                'source': default_source,
                'stock_id': stock_id,
            }
            if current is not None
            else None,
            removal=data.get(f'{part_type}-removed', 'keep'),
        )

    @staticmethod
    def validate_parts(data, context, count_switches=False):
        chosen = {}
        switch_count = None
        step = None
        for part in context['parts']:
            choice = part.validate(data)
            if choice is not None:
                chosen[part.type] = choice
                if count_switches and part.type == 'switch':
                    switch_count = part.validate_switch_count(data, choice)
            if part.error and step is None:
                step = part.type

        if not context['details_form'].is_valid() and step is None:
            step = 'details'

        return KeyboardSubmission(
            details_form=context['details_form'],
            chosen=chosen,
            removal={part.type: part.removal for part in context['parts']},
            switch_count=switch_count,
            step=step,
        )

    def validate_prebuilt(self, data):
        stock_id = data.get('prebuilt', '')
        stock_kb = (
            StockKeyboard.objects.filter(pk=stock_id).first()
            if is_id(stock_id)
            else None
        )

        if stock_kb is None:
            return None, 'Choose a prebuilt keyboard.'
        if Inventory.objects.filter(user=self.user, keyboard__stock=stock_kb).exists():
            # keyboard_inventory looks these up by stock board, so one per user
            return None, 'That prebuilt is already in your inventory.'
        return stock_kb, None
