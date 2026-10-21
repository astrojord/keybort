from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict

from . import const
from .forms import (
    CustomKeyboardDetailsForm,
    CustomKeycapsForm,
    CustomKitForm,
    CustomPlateForm,
    CustomStabilizerForm,
    CustomSwitchForm,
)
from .models import (
    CustomKeyboard,
    CustomKeycaps,
    CustomKit,
    CustomPlate,
    CustomStabilizer,
    CustomSwitch,
    Inventory,
    Keyboard,
    Keycaps,
    Kit,
    Plate,
    Stabilizer,
    StockKeyboard,
    StockKeycaps,
    StockKit,
    StockPlate,
    StockStabilizer,
    StockSwitch,
    Switch,
)


class KeyboardManager:
    def __init__(self, user):
        self.user = user

        # part type: wrapper model, custom model, stock model, custom form
        self.PART_MODELS = {
            'kit': (Kit, CustomKit, StockKit, CustomKitForm),
            'switch': (Switch, CustomSwitch, StockSwitch, CustomSwitchForm),
            'keycaps': (Keycaps, CustomKeycaps, StockKeycaps, CustomKeycapsForm),
            'plate': (Plate, CustomPlate, StockPlate, CustomPlateForm),
            'stabilizer': (
                Stabilizer,
                CustomStabilizer,
                StockStabilizer,
                CustomStabilizerForm,
            ),
        }

    # lookups

    def keyboard_inventory(self, kb_id, stock):
        lookup = 'keyboard__stock' if stock else 'keyboard__custom'
        return (
            Inventory.objects.filter(user=self.user, **{lookup: kb_id})
            .select_related('keyboard__custom', 'keyboard__stock')
            .first()
        )

    def standalone_parts(self):
        related = [
            f'{part_type}__{source}'
            for part_type in self.PART_MODELS
            for source in ('custom', 'stock')
        ]
        return Inventory.objects.filter(
            user=self.user, keyboard__isnull=True
        ).select_related(*related)

    def standalone_part(self, inv_id):
        return self.standalone_parts().filter(pk=inv_id).first()

    def visible_part(self, part_type, part_id, stock):
        _, custom_model, stock_model, _ = self.PART_MODELS[part_type]
        obj = (
            (stock_model if stock else custom_model).objects.filter(pk=part_id).first()
        )
        if obj is None or stock:
            return obj

        owned = (
            self.user.is_authenticated
            and Inventory.objects.filter(
                Q(**{f'{part_type}__custom': obj})
                | Q(**{f'keyboard__custom__{part_type}__custom': obj}),
                user=self.user,
            ).exists()
        )
        return obj if owned else None

    # table rows

    def keyboard_rows(self):
        keyboards = [
            inv.obj
            for inv in Inventory.objects.filter(user=self.user)
            .exclude(keyboard__isnull=True)
            .prefetch_related('kit', 'keycaps', 'switch', 'plate', 'stabilizer')
        ]
        return [self.keyboard_row(kb) for kb in keyboards]

    def part_rows(self):
        rows = [self.part_row(inv) for inv in self.standalone_parts()]
        order = list(self.PART_MODELS)
        rows.sort(key=lambda row: (order.index(row['type']), row['name'].lower()))
        return rows

    @staticmethod
    def part_obj(part):
        # custom keyboards point at wrappers (Kit, Switch, ...), stock keyboards point straight at Stock* parts
        return part.obj if hasattr(part, 'obj') else part

    @staticmethod
    def row_id(kb):
        return f'keyboard-{"stock" if kb.stock else "custom"}-{kb.pk}'

    @classmethod
    def keyboard_row(cls, kb):
        data = {
            'id': kb.pk,
            'row_id': cls.row_id(kb),
            'url_params': f'id={kb.pk}&stock={int(kb.stock)}',
            'stock': kb.stock,
            'notes': kb.notes,
        }

        if kb.kit:
            kit = cls.part_obj(kb.kit)
            data.update(
                {
                    'kit_url_params': f'type=kit&id={kit.pk}&stock={int(kit.stock)}',
                    'kit_str': f'{kit.brand} {kit.name}',
                    'pcb': kit.pcb,
                }
            )

        if kb.switch:
            switch = cls.part_obj(kb.switch)
            data.update(
                {
                    'switches_url_params': f'type=switch&id={switch.pk}&stock={int(switch.stock)}',
                    'switches_str': f'{switch.brand} {switch.name}',
                    'switch_count': getattr(kb, 'switch_count', None),
                }
            )

        for part_type in ('keycaps', 'plate', 'stabilizer'):
            part = getattr(kb, part_type)
            if part:
                obj = cls.part_obj(part)
                data[f'{part_type}_url_params'] = (
                    f'type={part_type}&id={obj.pk}&stock={int(obj.stock)}'
                )
                data[f'{part_type}_str'] = str(obj)

        return data

    @classmethod
    def board_switch_count(cls, kb, fallback=1):
        """switches on a board: what it recorded, else one per key on its kit"""
        count = getattr(kb, 'switch_count', None)
        if not count and kb.kit:
            count = cls.part_obj(kb.kit).total_keys
        return count or fallback

    @classmethod
    def part_type_of(cls, inv):
        return next(
            part_type
            for part_type in cls.PART_MODELS
            if getattr(inv, f'{part_type}_id')
        )

    @staticmethod
    def part_name(obj):
        # plates have no brand/name, their __str__ describes them
        name = ' '.join(
            filter(None, [getattr(obj, 'brand', None), getattr(obj, 'name', None)])
        )
        return name or str(obj)

    @staticmethod
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

    @classmethod
    def part_row(cls, inv):
        part_type = cls.part_type_of(inv)
        obj = getattr(inv, part_type).obj
        return {
            'id': inv.pk,
            'row_id': f'part-{inv.pk}',
            'type': part_type,
            'type_label': const.PART_SINGULARS[part_type],
            'name': cls.part_name(obj),
            'stock': obj.stock,
            'quantity': inv.quantity,
            'info': cls.part_info(part_type, obj),
            'detail_params': f'type={part_type}&id={obj.pk}&stock={int(obj.stock)}',
        }

    # modal form state

    def keyboard_form_context(self, action_url, data=None, current=None, kind=None):
        data = data or {}
        # kit is required (CustomKeyboard.__str__ depends on it)
        parts = [
            self.part_choice(
                part_type,
                data,
                current=getattr(current, part_type, None),
                required=part_type == 'kit',
                owned=self.owned_parts(part_type),
            )
            for part_type in self.PART_MODELS
        ]
        switch_default = (
            self.board_switch_count(current, fallback='')
            if current and current.switch
            else ''
        )
        parts[list(self.PART_MODELS).index('switch')]['count'] = data.get(
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

        stock_keyboards = StockKeyboard.objects.select_related('kit')
        if kind == 'prebuilt' and not stock_keyboards:
            kind = None
        step = {'prebuilt': 'prebuilt', 'custom': parts[0]['type']}.get(kind)

        return {
            'action_url': action_url,
            'editing': current is not None,
            'from_prebuilt': current is not None and current.stock,
            'kind': data.get('kind', kind or 'custom'),
            'step': step,
            'stock_keyboards': stock_keyboards,
            'prebuilt_id': data.get('prebuilt', ''),
            'prebuilt_error': None,
            'parts': parts,
            'details_form': details_form,
        }

    def owned_parts(self, part_type):
        return self.standalone_parts().filter(**{f'{part_type}__isnull': False})

    @classmethod
    def part_choice(cls, part_type, data, current=None, required=False, owned=None):
        _, _, stock_model, form_class = cls.PART_MODELS[part_type]
        label = const.PART_STEP_LABELS[part_type]
        stock_options = stock_model.objects.all()
        owned_options = None
        if owned is not None:
            owned_options = []
            for row in owned:
                obj = getattr(row, part_type).obj
                owned_options.append(
                    {
                        'id': row.pk,
                        'name': cls.part_name(obj),
                        'stock': obj.stock,
                        'quantity': row.quantity,
                        'total_keys': getattr(obj, 'total_keys', None),
                    }
                )
        instance = None
        stock_id = ''
        if current is None:
            if not required:
                default_source = 'none'
            elif owned_options:
                default_source = 'owned'
            elif stock_options:
                default_source = 'stock'
            else:
                default_source = 'custom'
        elif isinstance(current, stock_model):
            default_source, stock_id = 'stock', str(current.pk)
        elif current.stock_id:
            default_source, stock_id = 'stock', str(current.stock_id)
        else:
            default_source, instance = 'custom', current.custom

        source = data.get(f'{part_type}-source', default_source)
        return {
            'type': part_type,
            'label': label,
            'required': required,
            'source': source,
            'stock_options': stock_options,
            'stock_id': data.get(f'{part_type}-stock', stock_id),
            'owned_rows': owned,
            'owned_options': owned_options,
            'owned_id': data.get(f'{part_type}-owned', ''),
            # stock + custom, plus "from my parts" and skip when they apply
            'source_cards': 2 + (owned is not None) + (not required),
            # switch count, filled in by keyboard_form_context for the switch step
            'count': None,
            'form': form_class(
                (data or None) if source == 'custom' else None,
                prefix=part_type,
                instance=instance,
            ),
            'error': None,
            'current': {
                'name': str(cls.part_obj(current)),
                'source': default_source,
                'stock_id': stock_id,
            }
            if current is not None
            else None,
            'removal': data.get(f'{part_type}-removed', 'keep'),
        }

    # for the "which do you still have" checklist
    def keyboard_delete_parts(self, kb):
        parts = []
        for part_type in self.PART_MODELS:
            part = getattr(kb, part_type)
            if part is not None:
                obj = self.part_obj(part)
                label = const.PART_STEP_LABELS[part_type]
                name = str(obj)
                if part_type == 'switch':
                    name = f'{name} ×{self.board_switch_count(kb)}'
                parts.append(
                    {
                        'type': part_type,
                        'label': label,
                        'name': name,
                        'stock': obj.stock,
                        'part': part,
                    }
                )
        return parts

    def add_part_context(self, data=None, part_type=None):
        data = data or {}
        return {
            'part_type': data.get('type', part_type or 'kit'),
            'parts': [
                self.part_choice(t, data, required=True) for t in self.PART_MODELS
            ],
            'quantity': data.get('quantity', '1'),
            'quantity_error': None,
            'step': part_type,
        }

    def edit_part_context(self, inv, action_url, data=None):
        part_type = self.part_type_of(inv)
        wrapper = getattr(inv, part_type)
        form = None
        if wrapper.custom_id:
            form = self.PART_MODELS[part_type][3](
                data, prefix=part_type, instance=wrapper.custom
            )
        return {
            'inv': inv,
            'name': self.part_name(wrapper.obj),
            'type_label': const.PART_SINGULARS[part_type],
            'form': form,
            'quantity': data.get('quantity', '') if data else inv.quantity,
            'quantity_error': None,
            'action_url': action_url,
        }

    def delete_part_context(self, inv, action_url):
        part_type = self.part_type_of(inv)
        wrapper = getattr(inv, part_type)
        return {
            'inv': inv,
            'name': self.part_name(wrapper.obj),
            'type_label': const.PART_SINGULARS[part_type],
            'stock': bool(wrapper.stock_id),
            'action_url': action_url,
        }

    # validation

    @staticmethod
    def parse_quantity(value):
        value = (value or '').strip()
        return int(value) if value.isdigit() and int(value) > 0 else None

    @staticmethod
    def validate_part_choice(data, part):
        match part['source']:
            case 'stock':
                stock_id = data.get(f'{part["type"]}-stock', '')
                obj = (
                    part['stock_options'].filter(pk=stock_id).first()
                    if stock_id.isdigit()
                    else None
                )
                if obj is not None:
                    return ('stock', obj)
                part['error'] = f'Choose a stock option for {part["label"].lower()}.'
            case 'custom':
                if part['form'].is_valid():
                    return ('custom', part['form'])
                part['error'] = 'Some of these details need fixing.'
            case 'owned' if part['owned_rows'] is not None:
                row_id = data.get(f'{part["type"]}-owned', '')
                row = (
                    part['owned_rows'].filter(pk=row_id).first()
                    if row_id.isdigit()
                    else None
                )
                if row is not None:
                    return ('owned', row)
                part['error'] = f'Choose {part["label"].lower()} from your parts.'
            case 'none' if not part['required']:
                pass
            case _:
                part['error'] = (
                    f'Choose a stock {part["label"].lower()} or enter a custom one.'
                )
        return None

    def validate_custom_keyboard(self, data, context):
        chosen = {}
        for part in context['parts']:
            choice = self.validate_part_choice(data, part)
            if choice is not None:
                chosen[part['type']] = choice
            if part['type'] == 'switch' and choice is not None:
                context['switch_count'] = self._validate_switch_count(
                    data, part, choice
                )
            if part['error'] and context['step'] is None:
                context['step'] = part['type']

        if not context['details_form'].is_valid() and context['step'] is None:
            context['step'] = 'details'

        return None if context['step'] is not None else chosen

    def _validate_switch_count(self, data, part, choice):
        count = self.parse_quantity(data.get('switch-count'))
        source, value = choice
        if count is None:
            part['error'] = 'Enter how many switches are on the board.'
        elif source == 'owned' and count > value.quantity:
            part['error'] = f'You only have {value.quantity} of those switches.'
        return count

    # keyboard saves

    def add_prebuilt(self, context, data):
        stock_id = data.get('prebuilt', '')
        stock_kb = (
            StockKeyboard.objects.filter(pk=stock_id).first()
            if stock_id.isdigit()
            else None
        )

        if stock_kb is None:
            context['prebuilt_error'] = 'Choose a prebuilt keyboard.'
        elif Inventory.objects.filter(
            user=self.user, keyboard__stock=stock_kb
        ).exists():
            # keyboard_inventory looks these up by stock board, so one per user
            context['prebuilt_error'] = 'That prebuilt is already in your inventory.'
        else:
            # Keyboard.stock is one-to-one, every user shares the same wrapper for a stock board
            keyboard, _ = Keyboard.objects.get_or_create(stock=stock_kb)
            Inventory.objects.create(user=self.user, keyboard=keyboard)
            return stock_kb

        context['step'] = 'prebuilt'
        return None

    def add_custom(self, context, data):
        chosen = self.validate_custom_keyboard(data, context)
        if chosen is None:
            return None

        with transaction.atomic():
            custom_kb = context['details_form'].save(commit=False)
            self._save_keyboard_parts(custom_kb, chosen, context.get('switch_count'))
            keyboard = Keyboard.objects.create(custom=custom_kb)
            Inventory.objects.create(user=self.user, keyboard=keyboard)

        return custom_kb

    def edit_keyboard(self, inventory, context, data):
        chosen = self.validate_custom_keyboard(data, context)
        if chosen is None:
            return None

        current = inventory.keyboard.obj
        with transaction.atomic():
            custom_kb = context['details_form'].save(commit=False)
            removal = {part['type']: part['removal'] for part in context['parts']}
            self._save_keyboard_parts(
                custom_kb, chosen, context.get('switch_count'), removal
            )
            if current.stock:
                inventory.keyboard = Keyboard.objects.create(custom=custom_kb)
                inventory.save()
                # the new build starts empty, so compare against the prebuilt's own parts
                for part_type in self.PART_MODELS:
                    old = getattr(current, part_type)
                    if old is not None and chosen.get(part_type) != ('stock', old):
                        quantity = (
                            self.board_switch_count(current)
                            if part_type == 'switch'
                            else 1
                        )
                        self.release_part(
                            part_type,
                            old,
                            keep=removal[part_type] != 'delete',
                            quantity=quantity,
                        )

        return custom_kb

    def delete_keyboard(self, inventory, keep):
        kb = inventory.keyboard.obj
        parts = self.keyboard_delete_parts(kb)
        with transaction.atomic():
            inventory.delete()
            if not kb.stock:
                # Keyboard.custom cascades, the prebuilt itself is catalog data and stays
                kb.delete()
            for part in parts:
                quantity = (
                    self.board_switch_count(kb) if part['type'] == 'switch' else 1
                )
                self.release_part(
                    part['type'],
                    part['part'],
                    keep=part['type'] in keep,
                    quantity=quantity,
                )

    def _save_keyboard_parts(self, custom_kb, chosen, switch_count=None, removal=None):
        removal = removal or {}
        old_switch_count = self.board_switch_count(custom_kb) if custom_kb.switch else 1
        custom_kb.switch_count = switch_count if 'switch' in chosen else None
        dropped = []
        taken = []
        for part_type, (wrapper_model, _, _, _) in self.PART_MODELS.items():
            old = getattr(custom_kb, part_type)
            source, value = chosen.get(part_type, ('none', None))

            if source == 'stock':
                # wrapper.stock is one-to-one, share the existing wrapper for a stock part
                wrapper, _ = wrapper_model.objects.get_or_create(stock=value)
            elif source == 'owned':
                wrapper = getattr(value, part_type)
                taken.append((part_type, value))
            elif source == 'custom':
                obj = value.save(commit=False)
                # the form edits the current custom part in place, unless something else uses it too,
                # then the board gets its own copy and the original isn't coming off anything
                if obj.pk is not None and self.part_in_use(old, ignore=custom_kb):
                    obj.pk = None
                    obj._state.adding = True
                    old = None
                obj.save()
                if old is not None and old.custom_id == obj.pk:
                    wrapper = old
                else:
                    wrapper = wrapper_model.objects.create(custom=obj)
            else:
                wrapper = None

            if old is not None and old != wrapper:
                dropped.append((part_type, old))
            setattr(custom_kb, part_type, wrapper)

        custom_kb.save()

        for part_type, row in taken:
            self.take_from_parts(
                row, custom_kb.switch_count if part_type == 'switch' else 1
            )
        for part_type, old in dropped:
            quantity = old_switch_count if part_type == 'switch' else 1
            self.release_part(
                part_type,
                old,
                keep=removal.get(part_type) != 'delete',
                quantity=quantity,
            )

    # part saves

    def add_part(self, context, data):
        part_type = context['part_type']
        part = next(p for p in context['parts'] if p['type'] == part_type)
        choice = self.validate_part_choice(data, part)
        quantity = self.parse_quantity(data.get('quantity'))
        if quantity is None:
            context['quantity_error'] = const.QUANTITY_ERROR
        if choice is None or quantity is None:
            context['step'] = part_type
            return None

        source, value = choice
        wrapper_model = self.PART_MODELS[part_type][0]
        with transaction.atomic():
            if source == 'stock':
                wrapper, _ = wrapper_model.objects.get_or_create(stock=value)
            else:
                wrapper = wrapper_model.objects.create(custom=value.save())
            return self.add_to_parts(part_type, wrapper, quantity)

    def edit_part(self, context, data):
        """the saved inventory row, or None with errors on context"""
        inv, form = context['inv'], context['form']
        quantity = self.parse_quantity(data.get('quantity'))
        if quantity is None:
            context['quantity_error'] = const.QUANTITY_ERROR
        form_valid = form is None or form.is_valid()
        if quantity is None or not form_valid:
            return None

        with transaction.atomic():
            if form is not None:
                form.save()
            inv.quantity = quantity
            inv.save(update_fields=['quantity'])

        return self.standalone_parts().get(pk=inv.pk)

    def delete_part(self, inv):
        wrapper = getattr(inv, self.part_type_of(inv))
        with transaction.atomic():
            inv.delete()
            if wrapper.custom_id and not self.part_in_use(wrapper):
                # cascades to the wrapper
                wrapper.custom.delete()

    def release_part(self, part_type, part, keep, quantity=1):
        if not hasattr(part, 'obj'):
            if keep:
                wrapper, _ = self.PART_MODELS[part_type][0].objects.get_or_create(
                    stock=part
                )
                self.add_to_parts(part_type, wrapper, quantity)
            return

        if keep:
            # stacks onto a row of the same part, e.g. the rest of a set that only partly went onto the board
            self.add_to_parts(part_type, part, quantity)
        elif not part.stock_id and not self.part_in_use(part):
            # cascades to the wrapper
            part.custom.delete()

    def add_to_parts(self, part_type, wrapper, quantity=1):
        row = Inventory.objects.filter(
            user=self.user, keyboard__isnull=True, **{part_type: wrapper}
        ).first()
        if row is None:
            return Inventory.objects.create(
                user=self.user, quantity=quantity, **{part_type: wrapper}
            ), False
        row.quantity += quantity
        row.save(update_fields=['quantity'])
        return row, True

    @staticmethod
    def take_from_parts(row, quantity=1):
        row.refresh_from_db()
        row.quantity -= quantity
        if row.quantity > 0:
            row.save(update_fields=['quantity'])
        else:
            row.delete()

    @staticmethod
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
