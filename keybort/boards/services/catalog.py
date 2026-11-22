from django.db import transaction
from django.db.models import Q

from ..helpers.parts import PART_TYPES, part_fields, part_type_of
from ..helpers.rows import stock_part_row, stock_prebuilt_row
from ..models import CustomKeyboard, Inventory, Keyboard, StockKeyboard
from .base import UserScoped


class CatalogService(UserScoped):
    def owned_prebuilt_ids(self):
        if not self.user.is_authenticated:
            return set()
        return set(
            Inventory.objects.filter(
                user=self.user, keyboard__stock__isnull=False
            ).values_list('keyboard__stock', flat=True)
        )

    def stock_prebuilt_rows(self):
        owned = self.owned_prebuilt_ids()
        stock_keyboards = StockKeyboard.objects.select_related(
            'kit', 'switch', 'keycaps', 'plate', 'stabilizer'
        )
        rows = [stock_prebuilt_row(kb, kb.pk in owned) for kb in stock_keyboards]
        rows.sort(key=lambda row: row.name.lower())
        return rows

    def stock_part_quantities(self, part_type):
        if not self.user.is_authenticated:
            return {}
        return dict(
            Inventory.objects.filter(
                user=self.user,
                keyboard__isnull=True,
                **{f'{part_type}__stock__isnull': False},
            ).values_list(f'{part_type}__stock', 'quantity')
        )

    def stock_part_rows(self, part_type):
        quantities = self.stock_part_quantities(part_type)
        rows = [
            stock_part_row(part_type, obj, quantities.get(obj.pk, 0))
            for obj in PART_TYPES[part_type].stock.objects.all()
        ]
        rows.sort(key=lambda row: row.name.lower())
        return rows


def stock_part_usage(part_type, obj):
    return {
        'owner_count': Inventory.objects.filter(
            Q(**{f'{part_type}__stock': obj})
            | Q(**{f'keyboard__custom__{part_type}__stock': obj})
        )
        .values('user')
        .distinct()
        .count(),
        'prebuilts': [
            str(kb)
            for kb in StockKeyboard.objects.filter(**{part_type: obj}).select_related(
                'kit'
            )
        ],
    }


def promote_to_catalog(inv):
    part_type = part_type_of(inv)
    wrapper = getattr(inv, part_type)
    spec = PART_TYPES[part_type]
    custom = wrapper.custom
    with transaction.atomic():
        stock = spec.stock.objects.create(**part_fields(custom, spec.custom))
        wrapper.custom, wrapper.stock = None, stock
        wrapper.save()
        custom.delete()
    return stock


def delete_stock_part(part_type, obj):
    spec = PART_TYPES[part_type]
    fields = part_fields(obj, spec.custom)
    with transaction.atomic():
        for wrapper in spec.wrapper.objects.filter(stock=obj):
            for rel in wrapper._meta.related_objects:
                rows = rel.related_model._base_manager.filter(
                    **{rel.field.name: wrapper}
                )
                for row in rows:
                    copy = spec.wrapper.objects.create(
                        custom=spec.custom.objects.create(**fields)
                    )
                    setattr(row, rel.field.name, copy)
                    row.save(update_fields=[rel.field.name])
        obj.delete()


def save_stock_keyboard(submission):
    with transaction.atomic():
        stock_kb = submission.details_form.save(commit=False)
        for part_type in PART_TYPES:
            source, value = submission.chosen.get(part_type, ('none', None))
            if source == 'custom':
                value = value.save()
            setattr(stock_kb, part_type, value)
        stock_kb.save()
    return stock_kb


def delete_stock_keyboard(stock_kb):
    with transaction.atomic():
        for inventory in Inventory.objects.filter(keyboard__stock=stock_kb):
            custom_kb = CustomKeyboard(
                bluetooth=stock_kb.bluetooth,
                wireless=stock_kb.wireless,
                notes=stock_kb.notes,
                references=stock_kb.references,
            )
            for part_type, spec in PART_TYPES.items():
                part = getattr(stock_kb, part_type)
                if part is not None:
                    wrapper, _ = spec.wrapper.objects.get_or_create(stock=part)
                    setattr(custom_kb, part_type, wrapper)
            custom_kb.save()
            inventory.keyboard = Keyboard.objects.create(custom=custom_kb)
            inventory.save(update_fields=['keyboard'])
        stock_kb.delete()
