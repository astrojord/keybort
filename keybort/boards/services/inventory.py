from functools import cached_property

from django.db import transaction
from django.db.models import Count, Q, Sum

from .. import const
from ..helpers.parts import (
    PART_TYPES,
    board_quantity,
    board_switch_count,
    part_in_use,
    part_obj,
    part_type_of,
    switch_kind,
)
from ..helpers.rows import keyboard_row, part_row
from ..helpers.stats import stat_breakdown, stat_leader
from ..models import CustomOrStock, Inventory, Keyboard, part_name
from .base import UserScoped


class PartService(UserScoped):
    def standalone_parts(self):
        related = [
            f'{part_type}__{source}'
            for part_type in PART_TYPES
            for source in ('custom', 'stock')
        ]
        return Inventory.objects.filter(
            user=self.user, keyboard__isnull=True
        ).select_related(*related)

    def standalone_part(self, inv_id):
        return self.standalone_parts().filter(pk=inv_id).first()

    def owned_parts(self, part_type):
        return self.standalone_parts().filter(**{f'{part_type}__isnull': False})

    def visible_part(self, part_type, part_id, stock):
        spec = PART_TYPES[part_type]
        obj = (spec.stock if stock else spec.custom).objects.filter(pk=part_id).first()
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

    def part_rows(self):
        rows = [part_row(inv) for inv in self.standalone_parts()]
        order = list(PART_TYPES)
        rows.sort(key=lambda row: (order.index(row.type), row.name.lower()))
        return rows

    def collect_stock_part(self, part_type, obj, quantity):
        wrapper, _ = PART_TYPES[part_type].wrapper.objects.get_or_create(stock=obj)
        return self.add_to_parts(part_type, wrapper, quantity)

    def add_part(self, part_type, choice, quantity):
        source, value = choice
        wrapper_model = PART_TYPES[part_type].wrapper
        with transaction.atomic():
            if source == 'stock':
                wrapper, _ = wrapper_model.objects.get_or_create(stock=value)
            else:
                wrapper = wrapper_model.objects.create(custom=value.save())
            return self.add_to_parts(part_type, wrapper, quantity)

    def edit_part(self, inv, form, quantity):
        with transaction.atomic():
            if form is not None:
                form.save()
            inv.quantity = quantity
            inv.save(update_fields=['quantity'])

        return self.standalone_parts().get(pk=inv.pk)

    def delete_part(self, inv):
        wrapper = getattr(inv, part_type_of(inv))
        with transaction.atomic():
            inv.delete()
            if wrapper.custom_id and not part_in_use(wrapper):
                # cascades to the wrapper
                wrapper.custom.delete()

    def release_part(self, part_type, part, keep, quantity=1):
        if not isinstance(part, CustomOrStock):
            if keep:
                wrapper, _ = PART_TYPES[part_type].wrapper.objects.get_or_create(
                    stock=part
                )
                self.add_to_parts(part_type, wrapper, quantity)
            return

        if keep:
            # stacks onto a row of the same part, e.g. the rest of a set that only partly went onto the board
            self.add_to_parts(part_type, part, quantity)
        elif not part.stock_id and not part_in_use(part):
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
        row.quantity = min(row.quantity + quantity, const.MAX_QUANTITY)
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


class KeyboardService(UserScoped):
    @cached_property
    def parts(self):
        return PartService(self.user)

    def keyboard_inventory(self, kb_id, stock):
        lookup = 'keyboard__stock' if stock else 'keyboard__custom'
        return (
            Inventory.objects.filter(user=self.user, **{lookup: kb_id})
            .select_related('keyboard__custom', 'keyboard__stock')
            .first()
        )

    def owned_keyboards(self):
        related = [
            path
            for part_type in PART_TYPES
            for path in (
                f'keyboard__custom__{part_type}__custom',
                f'keyboard__custom__{part_type}__stock',
                f'keyboard__stock__{part_type}',
            )
        ]
        return Inventory.objects.filter(
            user=self.user, keyboard__isnull=False
        ).select_related(*related)

    def keyboard_rows(self):
        return [keyboard_row(inv.obj) for inv in self.owned_keyboards()]

    def inventory_counts(self):
        standalone = Q(keyboard__isnull=True)
        return Inventory.objects.filter(user=self.user).aggregate(
            keyboard_count=Count('pk', filter=Q(keyboard__isnull=False)),
            prebuilt_count=Count('pk', filter=Q(keyboard__stock__isnull=False)),
            part_entries=Count('pk', filter=standalone),
            part_units=Sum('quantity', filter=standalone, default=0),
            switches_loose=Sum('quantity', filter=Q(switch__isnull=False), default=0),
        )

    def dashboard(self):
        counts = self.inventory_counts()
        owned = list(self.owned_keyboards().order_by('-pk'))
        keyboards = [inv.obj for inv in owned]

        return {
            **counts,
            'custom_count': counts['keyboard_count'] - counts['prebuilt_count'],
            'switches_on_boards': sum(
                board_switch_count(kb) for kb in keyboards if kb.switch
            ),
            'recent_keyboards': [keyboard_row(kb) for kb in keyboards[:5]],
            'owned_keyboards': owned,
        }

    def collection_stats(self):
        owned = list(self.owned_keyboards().order_by('-pk'))
        keyboards = [inv.obj for inv in owned]

        def parts(part_type):
            for kb in keyboards:
                part = getattr(kb, part_type)
                yield part_obj(part) if part else None

        def field(part_type, name):
            return [getattr(obj, name, None) for obj in parts(part_type)]

        switch_names = [part_name(obj) if obj else None for obj in parts('switch')]
        switch_kinds = [switch_kind(obj) for obj in parts('switch')]
        switch_types = [kind and kind['label'] for kind in switch_kinds]
        slugs_by_label = {
            kind['label']: kind['slug'] for kind in filter(None, switch_kinds)
        }
        type_breakdown = stat_breakdown('Switch type', switch_types)
        for row in type_breakdown['rows']:
            row['switch_kind'] = slugs_by_label.get(row['label'])
        switches_on_boards = sum(
            board_switch_count(kb) for kb in keyboards if kb.switch
        )
        switches_loose = self.inventory_counts()['switches_loose']

        return {
            'owned_keyboards': owned,
            'stats_keyboard_count': len(keyboards),
            'stats_leaders': [
                {
                    'label': 'Top switch',
                    'leader': stat_leader(switch_names),
                },
                {
                    'label': 'Top keycap brand',
                    'leader': stat_leader(field('keycaps', 'brand')),
                },
                {
                    'label': 'Top kit brand',
                    'leader': stat_leader(field('kit', 'brand')),
                },
            ],
            'switches_total': switches_on_boards + switches_loose,
            'switches_on_boards': switches_on_boards,
            'switches_loose': switches_loose,
            'stats_breakdowns': [
                stat_breakdown('Layout', field('kit', 'layout')),
                stat_breakdown('Size', field('kit', 'size')),
                type_breakdown,
                stat_breakdown('Switches', switch_names),
                stat_breakdown('Keycap brands', field('keycaps', 'brand')),
                stat_breakdown('Mount type', field('kit', 'mount_type')),
            ],
        }

    # for the "which do you still have" checklist
    @staticmethod
    def keyboard_delete_parts(kb):
        parts = []
        for part_type in PART_TYPES:
            part = getattr(kb, part_type)
            if part is not None:
                obj = part_obj(part)
                label = PART_TYPES[part_type].step_label
                name = str(obj)
                if part_type == 'switch':
                    name = f'{name} ×{board_switch_count(kb)}'
                parts.append(
                    {
                        'type': part_type,
                        'label': label,
                        'name': name,
                        'is_stock': obj.is_stock,
                        'part': part,
                    }
                )
        return parts

    def collect_prebuilt(self, stock_kb):
        # Keyboard.stock is one-to-one, every user shares the same wrapper for a stock board
        keyboard, _ = Keyboard.objects.get_or_create(stock=stock_kb)
        return Inventory.objects.create(user=self.user, keyboard=keyboard)

    def add_custom(self, submission):
        with transaction.atomic():
            custom_kb = submission.details_form.save(commit=False)
            self._save_keyboard_parts(custom_kb, submission)
            keyboard = Keyboard.objects.create(custom=custom_kb)
            Inventory.objects.create(user=self.user, keyboard=keyboard)

        return custom_kb

    def edit_keyboard(self, inventory, submission):
        current = inventory.keyboard.obj
        with transaction.atomic():
            custom_kb = submission.details_form.save(commit=False)
            self._save_keyboard_parts(custom_kb, submission)
            if current.is_stock:
                inventory.keyboard = Keyboard.objects.create(custom=custom_kb)
                inventory.save()
                # the new build starts empty, so compare against the prebuilt's own parts
                for part_type in PART_TYPES:
                    old = getattr(current, part_type)
                    if old is not None and submission.chosen.get(part_type) != (
                        'stock',
                        old,
                    ):
                        self.parts.release_part(
                            part_type,
                            old,
                            keep=submission.removal[part_type] != 'delete',
                            quantity=board_quantity(current, part_type),
                        )

        return custom_kb

    def delete_keyboard(self, inventory, keep):
        kb = inventory.keyboard.obj
        parts = self.keyboard_delete_parts(kb)
        with transaction.atomic():
            inventory.delete()
            if not kb.is_stock:
                # Keyboard.custom cascades, the prebuilt itself is catalog data and stays
                kb.delete()
            for part in parts:
                self.parts.release_part(
                    part['type'],
                    part['part'],
                    keep=part['type'] in keep,
                    quantity=board_quantity(kb, part['type']),
                )

    def _save_keyboard_parts(self, custom_kb, submission):
        chosen = submission.chosen
        old_switch_count = board_switch_count(custom_kb) if custom_kb.switch else 1
        custom_kb.switch_count = submission.switch_count if 'switch' in chosen else None
        dropped = []
        taken = []
        for part_type, spec in PART_TYPES.items():
            old = getattr(custom_kb, part_type)
            source, value = chosen.get(part_type, ('none', None))

            if source == 'stock':
                # wrapper.stock is one-to-one, share the existing wrapper for a stock part
                wrapper, _ = spec.wrapper.objects.get_or_create(stock=value)
            elif source == 'owned':
                wrapper = getattr(value, part_type)
                taken.append((part_type, value))
            elif source == 'custom':
                obj = value.save(commit=False)
                # the form edits the current custom part in place, unless something else uses it too,
                # then the board gets its own copy and the original isn't coming off anything
                if obj.pk is not None and part_in_use(old, ignore=custom_kb):
                    obj.pk = None
                    obj._state.adding = True
                    old = None
                obj.save()
                if old is not None and old.custom_id == obj.pk:
                    wrapper = old
                else:
                    wrapper = spec.wrapper.objects.create(custom=obj)
            else:
                wrapper = None

            if old is not None and old != wrapper:
                dropped.append((part_type, old))
            setattr(custom_kb, part_type, wrapper)

        custom_kb.save()

        for part_type, row in taken:
            self.parts.take_from_parts(
                row, custom_kb.switch_count if part_type == 'switch' else 1
            )
        for part_type, old in dropped:
            quantity = old_switch_count if part_type == 'switch' else 1
            self.parts.release_part(
                part_type,
                old,
                keep=submission.removal[part_type] != 'delete',
                quantity=quantity,
            )
