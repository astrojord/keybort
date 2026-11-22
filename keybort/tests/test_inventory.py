from boards import const
from boards.helpers.forms_context import ModalForms, parse_quantity
from boards.helpers.parts import part_in_use
from boards.models import (
    CustomKeyboard,
    CustomKit,
    CustomPlate,
    CustomSwitch,
    Inventory,
    Keyboard,
    Keycaps,
    Kit,
    Plate,
    Stabilizer,
    StockKeyboard,
    Switch,
    TypingResult,
)
from boards.services.inventory import KeyboardService, PartService
from boards.services.races import TypingService

from .base import (
    UserTestCase,
    custom_keyboard,
    custom_kit_wrapper,
    custom_switch_wrapper,
    prebuilt_in_inventory,
    stock_keyboard,
    stock_keycaps,
    stock_kit,
    stock_plate,
    stock_stabilizer,
    stock_switch,
)


class PartRowsTests(UserTestCase):
    def test_part_rows_sort_by_type_then_name(self):
        Inventory.objects.create(
            user=self.user, switch=Switch.objects.create(stock=stock_switch())
        )
        Inventory.objects.create(
            user=self.user, kit=custom_kit_wrapper(brand='Zeal', name='Zz')
        )
        Inventory.objects.create(
            user=self.user, kit=custom_kit_wrapper(brand='Akko', name='Aa')
        )
        names = [row['name'] for row in self.part_service.part_rows()]
        self.assertEqual(names, ['Akko Aa', 'Zeal Zz', 'Gateron Yellow'])

    def test_part_rows_skip_other_users_and_keyboards(self):
        Inventory.objects.create(user=self.other, kit=custom_kit_wrapper())
        custom_keyboard(self.user)
        self.assertEqual(self.part_service.part_rows(), [])


class KeyboardRowTests(UserTestCase):
    def test_prebuilt_row(self):
        stock_kb = prebuilt_in_inventory(self.user)
        row = self.kb_service.keyboard_rows()[0]
        self.assertEqual(row['row_id'], f'keyboard-stock-{stock_kb.pk}')
        self.assertEqual(row['ref'], f'stock-{stock_kb.pk}')
        self.assertEqual(row['url_params'], f'id={stock_kb.pk}&stock=1')
        self.assertTrue(row['stock'])
        self.assertEqual(row['kit_str'], 'Keychron Q1')
        self.assertEqual(row['switches_str'], 'Gateron Yellow')

    def test_custom_row(self):
        kb = custom_keyboard(self.user, switch=custom_switch_wrapper(), switch_count=68)
        row = self.kb_service.keyboard_rows()[0]
        self.assertEqual(row['row_id'], f'keyboard-custom-{kb.pk}')
        self.assertEqual(row['ref'], f'custom-{kb.pk}')
        self.assertFalse(row['stock'])
        self.assertEqual(row['kit_str'], 'KBDfans Tofu65')
        self.assertEqual(row['switch_count'], 68)

    def test_only_own_keyboards(self):
        custom_keyboard(self.other)
        self.assertEqual(self.kb_service.keyboard_rows(), [])


class KeyboardQueryTests(UserTestCase):
    def setUp(self):
        super().setUp()
        prebuilt_in_inventory(
            self.user,
            stock_keyboard(
                keycaps=stock_keycaps(),
                plate=stock_plate(),
                stabilizer=stock_stabilizer(),
            ),
        )
        custom_keyboard(
            self.user,
            switch=custom_switch_wrapper(),
            keycaps=Keycaps.objects.create(stock=stock_keycaps()),
            plate=Plate.objects.create(
                custom=CustomPlate.objects.create(material='Brass')
            ),
            stabilizer=Stabilizer.objects.create(stock=stock_stabilizer()),
        )
        custom_keyboard(
            self.user,
            kit=Kit.objects.create(stock=stock_kit(name='Q2')),
            switch=Switch.objects.create(stock=stock_switch()),
        )
        self.part_service.add_to_parts(
            'switch', Switch.objects.create(stock=stock_switch()), quantity=70
        )
        self.part_service.add_to_parts('kit', custom_kit_wrapper(), quantity=2)

    def test_keyboard_rows_use_one_query(self):
        with self.assertNumQueries(1):
            rows = self.kb_service.keyboard_rows()
        self.assertEqual(
            sorted(row['kit_str'] for row in rows),
            ['KBDfans Tofu65', 'Keychron Q1', 'Keychron Q2'],
        )

    def test_dashboard_uses_two_queries(self):
        with self.assertNumQueries(2):
            stats = self.kb_service.dashboard()
        self.assertEqual(stats['keyboard_count'], 3)
        self.assertEqual(stats['prebuilt_count'], 1)
        self.assertEqual(stats['custom_count'], 2)
        self.assertEqual(stats['switches_on_boards'], 82 + 1 + 82)
        self.assertEqual(len(stats['recent_keyboards']), 3)

    def test_collection_stats_use_two_queries(self):
        with self.assertNumQueries(2):
            stats = self.kb_service.collection_stats()
        self.assertEqual(stats['stats_keyboard_count'], 3)
        self.assertEqual(stats['switches_on_boards'], 82 + 1 + 82)

    def test_race_context_adds_one_query(self):
        owned = list(self.kb_service.owned_keyboards())
        raced = owned[0].keyboard_id
        for keyboard_id in (None, raced):
            TypingResult.objects.create(
                user=self.user,
                keyboard_id=keyboard_id,
                word_count=25,
                characters=150,
                duration_ms=30_000,
            )

        with self.assertNumQueries(1):
            context = TypingService(self.user).race_context(owned)

        self.assertEqual(len(context['race_boards']), 3)
        self.assertEqual(context['race_selected_board'], raced)
        self.assertEqual(
            [row['races'] for row in context['race_history']],
            [2, 1],
        )

    def test_inventory_counts_use_one_query(self):
        with self.assertNumQueries(1):
            counts = self.kb_service.inventory_counts()
        self.assertEqual(
            counts,
            {
                'keyboard_count': 3,
                'prebuilt_count': 1,
                'part_entries': 2,
                'part_units': 72,
                'switches_loose': 70,
            },
        )

    def test_inventory_counts_skip_other_users(self):
        self.assertEqual(
            KeyboardService(self.other).inventory_counts(),
            {
                'keyboard_count': 0,
                'prebuilt_count': 0,
                'part_entries': 0,
                'part_units': 0,
                'switches_loose': 0,
            },
        )


class CollectionStatsTests(UserTestCase):
    def test_collection_stats_read_custom_and_stock_boards(self):
        prebuilt_in_inventory(
            self.user,
            stock_keyboard(
                kit=stock_kit(layout='QWERTY', size='75'),
                keycaps=stock_keycaps(brand='GMK'),
            ),
        )
        custom_keyboard(
            self.user,
            kit=custom_kit_wrapper(layout='qwerty'),
            switch=Switch.objects.create(stock=stock_switch()),
            keycaps=Keycaps.objects.create(stock=stock_keycaps(brand='gmk')),
        )
        custom_keyboard(self.user)
        self.part_service.add_to_parts(
            'switch', Switch.objects.create(stock=stock_switch()), quantity=10
        )

        stats = self.kb_service.collection_stats()
        leaders = {stat['label']: stat['leader'] for stat in stats['stats_leaders']}
        breakdowns = {
            item['title']: [(row['label'], row['count']) for row in item['rows']]
            for item in stats['stats_breakdowns']
        }

        self.assertEqual(leaders['Top switch']['label'], 'Gateron Yellow')
        self.assertEqual(leaders['Top switch']['count'], 2)
        self.assertEqual(leaders['Top keycap brand']['count'], 2)
        self.assertEqual(breakdowns['Layout'][0][1], 2)
        self.assertEqual(breakdowns['Layout'][1], ('Not set', 1))
        self.assertEqual(breakdowns['Switch type'], [('Linear', 2), ('Not set', 1)])
        type_rows = next(
            item['rows']
            for item in stats['stats_breakdowns']
            if item['title'] == 'Switch type'
        )
        self.assertEqual([row['switch_kind'] for row in type_rows], ['linear', None])
        self.assertEqual(stats['switches_loose'], 10)
        self.assertEqual(
            stats['switches_total'],
            stats['switches_on_boards'] + stats['switches_loose'],
        )

    def test_collection_stats_without_keyboards(self):
        stats = self.kb_service.collection_stats()
        self.assertEqual(stats['stats_keyboard_count'], 0)
        self.assertIsNone(stats['stats_leaders'][0]['leader'])


class PartsInventoryTests(UserTestCase):
    def test_add_to_parts_creates_then_stacks(self):
        wrapper = Switch.objects.create(stock=stock_switch())
        row, stacked = self.part_service.add_to_parts('switch', wrapper, 70)
        self.assertFalse(stacked)
        same, stacked = self.part_service.add_to_parts('switch', wrapper, 20)
        self.assertTrue(stacked)
        self.assertEqual(same.pk, row.pk)
        self.assertEqual(same.quantity, 90)

    def test_add_to_parts_caps_stacked_quantity(self):
        wrapper = Switch.objects.create(stock=stock_switch())
        self.part_service.add_to_parts('switch', wrapper, const.MAX_QUANTITY)
        row, _ = self.part_service.add_to_parts('switch', wrapper, 5)
        row.refresh_from_db()
        self.assertEqual(row.quantity, const.MAX_QUANTITY)

    def test_add_to_parts_keeps_users_apart(self):
        wrapper = Switch.objects.create(stock=stock_switch())
        PartService(self.other).add_to_parts('switch', wrapper)
        _, stacked = self.part_service.add_to_parts('switch', wrapper)
        self.assertFalse(stacked)

    def test_take_from_parts(self):
        row = Inventory.objects.create(
            user=self.user, switch=custom_switch_wrapper(), quantity=90
        )
        PartService.take_from_parts(row, 60)
        row.refresh_from_db()
        self.assertEqual(row.quantity, 30)
        PartService.take_from_parts(row, 30)
        self.assertFalse(Inventory.objects.filter(pk=row.pk).exists())

    def test_part_in_use(self):
        wrapper = custom_kit_wrapper()
        self.assertFalse(part_in_use(wrapper))
        kb = CustomKeyboard.objects.create(kit=wrapper)
        self.assertTrue(part_in_use(wrapper))
        self.assertFalse(part_in_use(wrapper, ignore=kb))
        self.assertFalse(part_in_use(None))

    def test_release_stock_part_kept(self):
        switch = stock_switch()
        self.part_service.release_part('switch', switch, keep=True, quantity=82)
        row = Inventory.objects.get(user=self.user, switch__stock=switch)
        self.assertEqual(row.quantity, 82)

    def test_release_custom_part_dropped_deletes_it(self):
        wrapper = custom_switch_wrapper()
        custom_id = wrapper.custom_id
        self.part_service.release_part('switch', wrapper, keep=False)
        self.assertFalse(CustomSwitch.objects.filter(pk=custom_id).exists())
        self.assertFalse(Switch.objects.filter(pk=wrapper.pk).exists())

    def test_release_custom_part_still_in_use_survives(self):
        wrapper = custom_kit_wrapper()
        CustomKeyboard.objects.create(kit=wrapper)
        self.part_service.release_part('kit', wrapper, keep=False)
        self.assertTrue(Kit.objects.filter(pk=wrapper.pk).exists())


class VisiblePartTests(UserTestCase):
    def test_stock_is_visible_to_anyone(self):
        switch = stock_switch()
        self.assertEqual(
            self.part_service.visible_part('switch', switch.pk, True), switch
        )

    def test_own_standalone_custom_part(self):
        wrapper = custom_kit_wrapper()
        Inventory.objects.create(user=self.user, kit=wrapper)
        self.assertEqual(
            self.part_service.visible_part('kit', wrapper.custom_id, False),
            wrapper.custom,
        )

    def test_own_custom_part_on_a_keyboard(self):
        kb = custom_keyboard(self.user)
        self.assertEqual(
            self.part_service.visible_part('kit', kb.kit.custom_id, False),
            kb.kit.custom,
        )

    def test_someone_elses_custom_part_is_hidden(self):
        kb = custom_keyboard(self.other)
        self.assertIsNone(
            self.part_service.visible_part('kit', kb.kit.custom_id, False)
        )

    def test_missing(self):
        self.assertIsNone(self.part_service.visible_part('kit', 999999, True))


class AddPartTests(UserTestCase):
    def add(self, data):
        context = self.modal_forms.add_part_context(data)
        part_type = context['part_type']
        part = next(p for p in context['parts'] if p.type == part_type)
        choice = part.validate(data)
        quantity = parse_quantity(data.get('quantity'))
        if quantity is None:
            context['quantity_error'] = const.QUANTITY_ERROR
        if choice is None or quantity is None:
            context['step'] = part_type
            return context, None
        return context, self.part_service.add_part(part_type, choice, quantity)

    def test_add_stock_part(self):
        switch = stock_switch()
        data = {
            'type': 'switch',
            'switch-source': 'stock',
            'switch-stock': str(switch.pk),
            'quantity': '90',
        }
        _, (inv, stacked) = self.add(data)
        self.assertFalse(stacked)
        self.assertEqual(inv.switch.stock, switch)
        self.assertEqual(inv.quantity, 90)

        _, (again, stacked) = self.add(data)
        self.assertTrue(stacked)
        self.assertEqual(again.pk, inv.pk)
        self.assertEqual(again.quantity, 180)

    def test_add_custom_part(self):
        data = {
            'type': 'kit',
            'kit-source': 'custom',
            'kit-brand': 'KBDfans',
            'kit-name': 'Tofu65',
            'quantity': '1',
        }
        _, (inv, _) = self.add(data)
        self.assertEqual(inv.kit.custom.name, 'Tofu65')

    def test_custom_parts_never_stack(self):
        data = {
            'type': 'kit',
            'kit-source': 'custom',
            'kit-brand': 'KBDfans',
            'kit-name': 'Tofu65',
            'quantity': '1',
        }
        self.add(data)
        _, (_, stacked) = self.add(data)
        self.assertFalse(stacked)
        self.assertEqual(Inventory.objects.filter(user=self.user).count(), 2)

    def test_bad_quantity(self):
        switch = stock_switch()
        data = {
            'type': 'switch',
            'switch-source': 'stock',
            'switch-stock': str(switch.pk),
            'quantity': '0',
        }
        context, result = self.add(data)
        self.assertIsNone(result)
        self.assertEqual(context['quantity_error'], const.QUANTITY_ERROR)
        self.assertEqual(context['step'], 'switch')
        self.assertFalse(Inventory.objects.exists())

    def test_missing_stock_choice(self):
        context, result = self.add(
            {'type': 'switch', 'switch-source': 'stock', 'quantity': '1'}
        )
        self.assertIsNone(result)
        switch = next(p for p in context['parts'] if p.type == 'switch')
        self.assertIsNotNone(switch.error)

    def test_invalid_custom_form(self):
        _context, result = self.add(
            {
                'type': 'kit',
                'kit-source': 'custom',
                'kit-brand': 'KBDfans',
                'quantity': '1',
            }
        )
        self.assertIsNone(result)
        self.assertFalse(CustomKit.objects.exists())

    def test_context_opens_on_requested_type(self):
        context = self.modal_forms.add_part_context(part_type='plate')
        self.assertEqual(context['part_type'], 'plate')
        self.assertEqual(context['step'], 'plate')


class EditDeletePartTests(UserTestCase):
    def test_edit_custom_part_and_quantity(self):
        inv = Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        data = {'quantity': '3', 'kit-brand': 'KBDfans', 'kit-name': 'Tofu60'}
        context = self.modal_forms.edit_part_context(inv, '/edit', data)
        self.assertTrue(context['form'].is_valid())
        inv = self.part_service.edit_part(inv, context['form'], 3)
        self.assertEqual(inv.quantity, 3)
        self.assertEqual(inv.kit.custom.name, 'Tofu60')

    def test_edit_stock_part_only_changes_quantity(self):
        inv = Inventory.objects.create(
            user=self.user, switch=Switch.objects.create(stock=stock_switch())
        )
        context = self.modal_forms.edit_part_context(inv, '/edit', {'quantity': '45'})
        self.assertIsNone(context['form'])
        self.assertEqual(self.part_service.edit_part(inv, None, 45).quantity, 45)

    def test_delete_custom_part_removes_it(self):
        wrapper = custom_kit_wrapper()
        inv = Inventory.objects.create(user=self.user, kit=wrapper)
        self.part_service.delete_part(inv)
        self.assertFalse(Inventory.objects.exists())
        self.assertFalse(CustomKit.objects.exists())

    def test_delete_stock_part_keeps_catalog(self):
        plate = stock_plate()
        inv = Inventory.objects.create(
            user=self.user, plate=Plate.objects.create(stock=plate)
        )
        self.part_service.delete_part(inv)
        self.assertFalse(Inventory.objects.exists())
        plate.refresh_from_db()

    def test_standalone_part_is_scoped_to_user(self):
        inv = Inventory.objects.create(user=self.other, kit=custom_kit_wrapper())
        self.assertIsNone(self.part_service.standalone_part(inv.pk))


class AddPrebuiltTests(UserTestCase):
    def add(self, prebuilt_id, user=None):
        user = user or self.user
        data = {'kind': 'prebuilt', 'prebuilt': str(prebuilt_id)}
        context = ModalForms(user).keyboard_form_context('/add', data)
        stock_kb, error = ModalForms(user).validate_prebuilt(data)
        if error is not None:
            context['step'] = 'prebuilt'
            context['prebuilt_error'] = error
            return context, None
        KeyboardService(user).collect_prebuilt(stock_kb)
        return context, stock_kb

    def test_adds_to_inventory(self):
        stock_kb = stock_keyboard()
        _, result = self.add(stock_kb.pk)
        self.assertEqual(result, stock_kb)
        self.assertTrue(
            Inventory.objects.filter(user=self.user, keyboard__stock=stock_kb).exists()
        )

    def test_one_per_user(self):
        stock_kb = stock_keyboard()
        self.add(stock_kb.pk)
        context, result = self.add(stock_kb.pk)
        self.assertIsNone(result)
        self.assertEqual(context['step'], 'prebuilt')
        self.assertIsNotNone(context['prebuilt_error'])

    def test_users_share_the_wrapper(self):
        stock_kb = stock_keyboard()
        self.add(stock_kb.pk)
        self.add(stock_kb.pk, self.other)
        self.assertEqual(Keyboard.objects.filter(stock=stock_kb).count(), 1)
        self.assertEqual(Inventory.objects.filter(keyboard__stock=stock_kb).count(), 2)

    def test_unknown_prebuilt(self):
        context, result = self.add(999999)
        self.assertIsNone(result)
        self.assertIsNotNone(context['prebuilt_error'])


class AddCustomTests(UserTestCase):
    def setUp(self):
        super().setUp()
        self.kit_data = {
            'kind': 'custom',
            'kit-source': 'custom',
            'kit-brand': 'KBDfans',
            'kit-name': 'Tofu65',
        }

    def add(self, **extra):
        data = {**self.kit_data, **extra}
        context = self.modal_forms.keyboard_form_context('/add', data)
        submission = ModalForms.validate_parts(data, context, count_switches=True)
        if submission.step is not None:
            context['step'] = submission.step
            return context, None
        return context, self.kb_service.add_custom(submission)

    def test_custom_kit_only(self):
        _, kb = self.add(**{'details-notes': 'first build'})
        self.assertEqual(kb.kit.custom.name, 'Tofu65')
        self.assertIsNone(kb.switch)
        self.assertEqual(kb.notes, 'first build')
        self.assertTrue(
            Inventory.objects.filter(user=self.user, keyboard__custom=kb).exists()
        )

    def test_stock_switches_with_count(self):
        switch = stock_switch()
        _, kb = self.add(
            **{
                'switch-source': 'stock',
                'switch-stock': str(switch.pk),
                'switch-count': '68',
            }
        )
        self.assertEqual(kb.switch.stock, switch)
        self.assertEqual(kb.switch_count, 68)

    def test_shares_stock_wrapper(self):
        switch = stock_switch()
        existing = Switch.objects.create(stock=switch)
        _, kb = self.add(
            **{
                'switch-source': 'stock',
                'switch-stock': str(switch.pk),
                'switch-count': '68',
            }
        )
        self.assertEqual(kb.switch, existing)

    def test_switches_from_parts_are_taken(self):
        row = Inventory.objects.create(
            user=self.user, switch=custom_switch_wrapper(), quantity=90
        )
        _, kb = self.add(
            **{
                'switch-source': 'owned',
                'switch-owned': str(row.pk),
                'switch-count': '68',
            }
        )
        self.assertEqual(kb.switch, row.switch)
        row.refresh_from_db()
        self.assertEqual(row.quantity, 22)

    def test_using_every_owned_switch_clears_the_row(self):
        row = Inventory.objects.create(
            user=self.user, switch=custom_switch_wrapper(), quantity=68
        )
        self.add(
            **{
                'switch-source': 'owned',
                'switch-owned': str(row.pk),
                'switch-count': '68',
            }
        )
        self.assertFalse(Inventory.objects.filter(pk=row.pk).exists())

    def test_cant_take_more_switches_than_owned(self):
        row = Inventory.objects.create(
            user=self.user, switch=custom_switch_wrapper(), quantity=50
        )
        context, kb = self.add(
            **{
                'switch-source': 'owned',
                'switch-owned': str(row.pk),
                'switch-count': '68',
            }
        )
        self.assertIsNone(kb)
        self.assertEqual(context['step'], 'switch')
        row.refresh_from_db()
        self.assertEqual(row.quantity, 50)

    def test_cant_take_someone_elses_parts(self):
        row = Inventory.objects.create(
            user=self.other, switch=custom_switch_wrapper(), quantity=90
        )
        context, kb = self.add(
            **{
                'switch-source': 'owned',
                'switch-owned': str(row.pk),
                'switch-count': '68',
            }
        )
        self.assertIsNone(kb)
        self.assertEqual(context['step'], 'switch')

    def test_switch_count_required(self):
        switch = stock_switch()
        context, kb = self.add(
            **{'switch-source': 'stock', 'switch-stock': str(switch.pk)}
        )
        self.assertIsNone(kb)
        self.assertEqual(context['step'], 'switch')

    def test_kit_required(self):
        self.kit_data = {'kind': 'custom', 'kit-source': 'none'}
        context, kb = self.add()
        self.assertIsNone(kb)
        self.assertEqual(context['step'], 'kit')
        self.assertFalse(CustomKeyboard.objects.exists())

    def test_first_broken_step_wins(self):
        self.kit_data = {
            'kind': 'custom',
            'kit-source': 'custom',
            'kit-brand': 'KBDfans',
        }
        context, _ = self.add(**{'switch-source': 'stock'})
        self.assertEqual(context['step'], 'kit')


class EditKeyboardTests(UserTestCase):
    def edit(self, inventory, data):
        context = self.modal_forms.keyboard_form_context(
            '/edit', data, current=inventory.keyboard.obj
        )
        submission = ModalForms.validate_parts(data, context, count_switches=True)
        if submission.step is not None:
            context['step'] = submission.step
            return context, None
        return context, self.kb_service.edit_keyboard(inventory, submission)

    def test_editing_prebuilt_makes_a_custom_build(self):
        stock_kb = prebuilt_in_inventory(self.user)
        inventory = self.kb_service.keyboard_inventory(stock_kb.pk, True)
        data = {
            'kit-source': 'stock',
            'kit-stock': str(stock_kb.kit.pk),
            'switch-source': 'none',
        }
        _, kb = self.edit(inventory, data)

        inventory.refresh_from_db()
        self.assertEqual(inventory.keyboard.custom, kb)
        self.assertEqual(kb.kit.stock, stock_kb.kit)
        self.assertTrue(StockKeyboard.objects.filter(pk=stock_kb.pk).exists())

        released = Inventory.objects.get(user=self.user, switch__stock=stock_kb.switch)
        self.assertEqual(released.quantity, 82)
        self.assertFalse(
            Inventory.objects.filter(user=self.user, kit__isnull=False).exists()
        )

    def test_editing_prebuilt_can_drop_parts(self):
        stock_kb = prebuilt_in_inventory(self.user)
        inventory = self.kb_service.keyboard_inventory(stock_kb.pk, True)
        data = {
            'kit-source': 'stock',
            'kit-stock': str(stock_kb.kit.pk),
            'switch-source': 'none',
            'switch-removed': 'delete',
        }
        self.edit(inventory, data)
        self.assertFalse(
            Inventory.objects.filter(user=self.user, switch__isnull=False).exists()
        )

    def test_edit_custom_part_in_place(self):
        kb = custom_keyboard(self.user)
        kit_wrapper = kb.kit
        inventory = self.kb_service.keyboard_inventory(kb.pk, False)
        _, kb = self.edit(
            inventory,
            {'kit-source': 'custom', 'kit-brand': 'KBDfans', 'kit-name': 'Tofu60'},
        )
        self.assertEqual(kb.kit, kit_wrapper)
        self.assertEqual(kb.kit.custom.name, 'Tofu60')
        self.assertEqual(CustomKit.objects.count(), 1)

    def test_swapped_out_custom_switch_goes_to_parts(self):
        kb = custom_keyboard(self.user, switch=custom_switch_wrapper(), switch_count=60)
        old_switch = kb.switch
        new_switch = stock_switch()
        inventory = self.kb_service.keyboard_inventory(kb.pk, False)
        data = {
            'kit-source': 'custom',
            'kit-brand': 'KBDfans',
            'kit-name': 'Tofu65',
            'switch-source': 'stock',
            'switch-stock': str(new_switch.pk),
            'switch-count': '68',
        }
        _, kb = self.edit(inventory, data)
        self.assertEqual(kb.switch.stock, new_switch)
        self.assertEqual(kb.switch_count, 68)
        self.assertEqual(
            Inventory.objects.get(user=self.user, switch=old_switch).quantity, 60
        )

    def test_swapped_out_custom_switch_can_be_deleted(self):
        kb = custom_keyboard(self.user, switch=custom_switch_wrapper(), switch_count=60)
        custom_id = kb.switch.custom_id
        new_switch = stock_switch()
        inventory = self.kb_service.keyboard_inventory(kb.pk, False)
        data = {
            'kit-source': 'custom',
            'kit-brand': 'KBDfans',
            'kit-name': 'Tofu65',
            'switch-source': 'stock',
            'switch-stock': str(new_switch.pk),
            'switch-count': '68',
            'switch-removed': 'delete',
        }
        self.edit(inventory, data)
        self.assertFalse(CustomSwitch.objects.filter(pk=custom_id).exists())

    def test_invalid_edit_changes_nothing(self):
        kb = custom_keyboard(self.user)
        inventory = self.kb_service.keyboard_inventory(kb.pk, False)
        context, result = self.edit(
            inventory, {'kit-source': 'custom', 'kit-brand': '', 'kit-name': ''}
        )
        self.assertIsNone(result)
        self.assertEqual(context['step'], 'kit')
        kb.kit.custom.refresh_from_db()
        self.assertEqual(kb.kit.custom.name, 'Tofu65')

    def test_keyboard_inventory_is_scoped_to_user(self):
        kb = custom_keyboard(self.other)
        self.assertIsNone(self.kb_service.keyboard_inventory(kb.pk, False))


class DeleteKeyboardTests(UserTestCase):
    def test_delete_custom_keeps_checked_parts(self):
        kb = custom_keyboard(self.user, switch=custom_switch_wrapper(), switch_count=60)
        kit, switch = kb.kit, kb.switch
        self.kb_service.delete_keyboard(
            self.kb_service.keyboard_inventory(kb.pk, False), keep=['kit']
        )

        self.assertFalse(CustomKeyboard.objects.filter(pk=kb.pk).exists())
        self.assertFalse(Keyboard.objects.exists())
        self.assertTrue(
            Inventory.objects.filter(
                user=self.user, kit=kit, keyboard__isnull=True
            ).exists()
        )
        self.assertFalse(Switch.objects.filter(pk=switch.pk).exists())

    def test_delete_custom_returns_all_switches(self):
        kb = custom_keyboard(self.user, switch=custom_switch_wrapper(), switch_count=60)
        switch = kb.switch
        self.kb_service.delete_keyboard(
            self.kb_service.keyboard_inventory(kb.pk, False), keep=['kit', 'switch']
        )
        self.assertEqual(
            Inventory.objects.get(user=self.user, switch=switch).quantity, 60
        )

    def test_delete_prebuilt_keeps_catalog(self):
        stock_kb = prebuilt_in_inventory(self.user)
        self.kb_service.delete_keyboard(
            self.kb_service.keyboard_inventory(stock_kb.pk, True), keep=['switch']
        )

        self.assertTrue(StockKeyboard.objects.filter(pk=stock_kb.pk).exists())
        self.assertFalse(
            Inventory.objects.filter(user=self.user, keyboard__isnull=False).exists()
        )
        self.assertEqual(
            Inventory.objects.get(
                user=self.user, switch__stock=stock_kb.switch
            ).quantity,
            82,
        )
        self.assertFalse(
            Inventory.objects.filter(user=self.user, kit__isnull=False).exists()
        )

    def test_delete_parts_checklist(self):
        stock_kb = stock_keyboard(plate=stock_plate())
        parts = {
            part['type']: part
            for part in KeyboardService.keyboard_delete_parts(stock_kb)
        }
        self.assertEqual(set(parts), {'kit', 'switch', 'plate'})
        self.assertTrue(parts['switch']['name'].endswith('×82'))
