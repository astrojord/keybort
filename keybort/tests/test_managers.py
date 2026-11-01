from boards import const
from boards.managers import (
    KeyboardManager,
    ModalForms,
    PartManager,
    RowBuilder,
    board_switch_count,
    parse_quantity,
    part_in_use,
    part_name,
)
from boards.models import (
    CustomKeyboard,
    CustomKit,
    CustomPlate,
    CustomSwitch,
    Inventory,
    Keyboard,
    Kit,
    Plate,
    Profile,
    StockKeyboard,
    Switch,
)

from .base import (
    UserTestCase,
    custom_keyboard,
    custom_kit_wrapper,
    custom_switch_wrapper,
    prebuilt_in_inventory,
    stock_keyboard,
    stock_kit,
    stock_plate,
    stock_switch,
)


class PartDisplayTests(UserTestCase):
    def test_part_name_joins_brand_and_name(self):
        self.assertEqual(part_name(stock_kit()), 'Keychron Q1')

    def test_part_name_falls_back_to_str(self):
        self.assertEqual(part_name(CustomPlate(material='Brass')), 'Brass')

    def test_switch_info(self):
        switch = CustomSwitch(
            category='t',
            bottom_out_force=62.0,
            top_housing='pc',
            lubed=True,
            notes='hand lubed',
        )
        self.assertEqual(
            RowBuilder.part_info('switch', switch),
            'Tactile, 62gf, Polycarbonate top, lubed, hand lubed',
        )

    def test_kit_info(self):
        kit = CustomKit(size='65%', pcb='Hotswap')
        self.assertEqual(RowBuilder.part_info('kit', kit), '65%, Hotswap PCB')

    def test_part_row(self):
        inv = Inventory.objects.create(
            user=self.user, kit=custom_kit_wrapper(), quantity=2
        )
        row = RowBuilder.part_row(inv)
        self.assertEqual(row['row_id'], f'part-{inv.pk}')
        self.assertEqual(row['type'], 'kit')
        self.assertEqual(row['name'], 'KBDfans Tofu65')
        self.assertEqual(row['quantity'], 2)
        self.assertFalse(row['stock'])

    def test_part_columns_have_unique_sort_keys(self):
        keys = [column['key'] for column in RowBuilder.part_columns()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_part_columns_label_each_field(self):
        columns = RowBuilder.part_columns()
        labels = {column['key']: column['label'] for column in columns}
        self.assertEqual(labels['switch-stem'], 'Stem')
        self.assertEqual(labels['switch-category'], 'Type')
        self.assertEqual(labels['plate-half'], 'Half plate')

    def test_part_cells_line_up_with_columns(self):
        switch = CustomSwitch(
            stem='mx', peak_force=45.0, lubed=True, notes='hand lubed'
        )
        cells = RowBuilder.part_cells('switch', switch)
        columns = RowBuilder.part_columns()
        self.assertEqual(
            [cell['type'] for cell in cells], [column['type'] for column in columns]
        )
        values = {
            column['key']: cell['value']
            for column, cell in zip(columns, cells, strict=True)
        }
        self.assertEqual(values['switch-stem'], 'MX')
        self.assertEqual(values['switch-force'], '45gf / —')
        self.assertEqual(values['switch-lubed'], 'Yes')
        self.assertEqual(values['switch-filmed'], 'No')
        self.assertEqual(values['switch-notes'], 'hand lubed')

    def test_part_cells_flag_only_icon_fields(self):
        switch = CustomSwitch(stem='mx', lubed=True)
        cells = RowBuilder.part_cells('switch', switch)
        columns = RowBuilder.part_columns()
        flags = {
            column['key']: cell['flag']
            for column, cell in zip(columns, cells, strict=True)
            if cell['flag'] is not None
        }
        self.assertEqual(flags, {'switch-lubed': True, 'switch-filmed': False})

    def test_travel_column_label(self):
        labels = {c['key']: c['label'] for c in RowBuilder.part_columns()}
        self.assertEqual(labels['switch-travel_distance'], 'Travel')

    def test_force_combines_peak_then_bottom_out(self):
        switch = CustomSwitch(peak_force=55.0, bottom_out_force=65.0)
        self.assertEqual(RowBuilder.field_display(switch, 'force'), '55gf / 65gf')

    def test_housing_combines_top_and_bottom(self):
        switch = CustomSwitch(top_housing='pc', bottom_housing='nylon')
        self.assertEqual(
            RowBuilder.field_display(switch, 'housing'), 'Polycarbonate / Nylon'
        )

    def test_housing_marks_missing_side(self):
        switch = CustomSwitch(top_housing='pom')
        self.assertEqual(RowBuilder.field_display(switch, 'housing'), 'POM / —')

    def test_housing_blank_when_unset(self):
        self.assertEqual(RowBuilder.field_display(CustomSwitch(), 'housing'), '')

    def test_part_cells_blank_for_other_types(self):
        cells = RowBuilder.part_cells('switch', CustomSwitch(notes='hand lubed'))
        other_values = {cell['value'] for cell in cells if cell['type'] != 'switch'}
        self.assertEqual(other_values, {''})

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
        names = [row['name'] for row in self.part_manager.part_rows()]
        self.assertEqual(names, ['Akko Aa', 'Zeal Zz', 'Gateron Yellow'])

    def test_part_rows_skip_other_users_and_keyboards(self):
        Inventory.objects.create(user=self.other, kit=custom_kit_wrapper())
        custom_keyboard(self.user)
        self.assertEqual(self.part_manager.part_rows(), [])


class KeyboardRowTests(UserTestCase):
    def test_prebuilt_row(self):
        stock_kb = prebuilt_in_inventory(self.user)
        row = self.kb_manager.keyboard_rows()[0]
        self.assertEqual(row['row_id'], f'keyboard-stock-{stock_kb.pk}')
        self.assertEqual(row['url_params'], f'id={stock_kb.pk}&stock=1')
        self.assertTrue(row['stock'])
        self.assertEqual(row['kit_str'], 'Keychron Q1')
        self.assertEqual(row['switches_str'], 'Gateron Yellow')

    def test_custom_row(self):
        kb = custom_keyboard(self.user, switch=custom_switch_wrapper(), switch_count=68)
        row = self.kb_manager.keyboard_rows()[0]
        self.assertEqual(row['row_id'], f'keyboard-custom-{kb.pk}')
        self.assertFalse(row['stock'])
        self.assertEqual(row['kit_str'], 'KBDfans Tofu65')
        self.assertEqual(row['switch_count'], 68)

    def test_only_own_keyboards(self):
        custom_keyboard(self.other)
        self.assertEqual(self.kb_manager.keyboard_rows(), [])


class SwitchCountTests(UserTestCase):
    def test_recorded_count_wins(self):
        kb = CustomKeyboard(kit=custom_kit_wrapper(total_keys=68), switch_count=60)
        self.assertEqual(board_switch_count(kb), 60)

    def test_falls_back_to_kit_keys(self):
        kb = CustomKeyboard(kit=custom_kit_wrapper(total_keys=68))
        self.assertEqual(board_switch_count(kb), 68)
        self.assertEqual(board_switch_count(stock_keyboard()), 82)

    def test_falls_back_to_default(self):
        kb = CustomKeyboard(kit=custom_kit_wrapper())
        self.assertEqual(board_switch_count(kb), 1)
        self.assertEqual(board_switch_count(kb, fallback=''), '')


class ParseQuantityTests(UserTestCase):
    def test_accepts_positive_ints(self):
        self.assertEqual(parse_quantity('3'), 3)
        self.assertEqual(parse_quantity(' 90 '), 90)
        self.assertEqual(parse_quantity(str(const.MAX_QUANTITY)), const.MAX_QUANTITY)

    def test_rejects_everything_else(self):
        too_big = str(const.MAX_QUANTITY + 1)
        for value in ('0', '-1', '1.5', 'abc', '', None, '²', too_big, '1' * 5000):
            with self.subTest(value=value):
                self.assertIsNone(parse_quantity(value))


class PartsInventoryTests(UserTestCase):
    def test_add_to_parts_creates_then_stacks(self):
        wrapper = Switch.objects.create(stock=stock_switch())
        row, stacked = self.part_manager.add_to_parts('switch', wrapper, 70)
        self.assertFalse(stacked)
        same, stacked = self.part_manager.add_to_parts('switch', wrapper, 20)
        self.assertTrue(stacked)
        self.assertEqual(same.pk, row.pk)
        self.assertEqual(same.quantity, 90)

    def test_add_to_parts_caps_stacked_quantity(self):
        wrapper = Switch.objects.create(stock=stock_switch())
        self.part_manager.add_to_parts('switch', wrapper, const.MAX_QUANTITY)
        row, _ = self.part_manager.add_to_parts('switch', wrapper, 5)
        row.refresh_from_db()
        self.assertEqual(row.quantity, const.MAX_QUANTITY)

    def test_add_to_parts_keeps_users_apart(self):
        wrapper = Switch.objects.create(stock=stock_switch())
        PartManager(self.other).add_to_parts('switch', wrapper)
        _, stacked = self.part_manager.add_to_parts('switch', wrapper)
        self.assertFalse(stacked)

    def test_take_from_parts(self):
        row = Inventory.objects.create(
            user=self.user, switch=custom_switch_wrapper(), quantity=90
        )
        PartManager.take_from_parts(row, 60)
        row.refresh_from_db()
        self.assertEqual(row.quantity, 30)
        PartManager.take_from_parts(row, 30)
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
        self.part_manager.release_part('switch', switch, keep=True, quantity=82)
        row = Inventory.objects.get(user=self.user, switch__stock=switch)
        self.assertEqual(row.quantity, 82)

    def test_release_custom_part_dropped_deletes_it(self):
        wrapper = custom_switch_wrapper()
        custom_id = wrapper.custom_id
        self.part_manager.release_part('switch', wrapper, keep=False)
        self.assertFalse(CustomSwitch.objects.filter(pk=custom_id).exists())
        self.assertFalse(Switch.objects.filter(pk=wrapper.pk).exists())

    def test_release_custom_part_still_in_use_survives(self):
        wrapper = custom_kit_wrapper()
        CustomKeyboard.objects.create(kit=wrapper)
        self.part_manager.release_part('kit', wrapper, keep=False)
        self.assertTrue(Kit.objects.filter(pk=wrapper.pk).exists())


class VisiblePartTests(UserTestCase):
    def test_stock_is_visible_to_anyone(self):
        switch = stock_switch()
        self.assertEqual(
            self.part_manager.visible_part('switch', switch.pk, True), switch
        )

    def test_own_standalone_custom_part(self):
        wrapper = custom_kit_wrapper()
        Inventory.objects.create(user=self.user, kit=wrapper)
        self.assertEqual(
            self.part_manager.visible_part('kit', wrapper.custom_id, False),
            wrapper.custom,
        )

    def test_own_custom_part_on_a_keyboard(self):
        kb = custom_keyboard(self.user)
        self.assertEqual(
            self.part_manager.visible_part('kit', kb.kit.custom_id, False),
            kb.kit.custom,
        )

    def test_someone_elses_custom_part_is_hidden(self):
        kb = custom_keyboard(self.other)
        self.assertIsNone(
            self.part_manager.visible_part('kit', kb.kit.custom_id, False)
        )

    def test_missing(self):
        self.assertIsNone(self.part_manager.visible_part('kit', 999999, True))


class AddPartTests(UserTestCase):
    def add(self, data):
        context = self.modal_forms.add_part_context(data)
        return context, self.part_manager.add_part(context, data)

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
        switch = next(p for p in context['parts'] if p['type'] == 'switch')
        self.assertIsNotNone(switch['error'])

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
        inv = self.part_manager.edit_part(context, data)
        self.assertEqual(inv.quantity, 3)
        self.assertEqual(inv.kit.custom.name, 'Tofu60')

    def test_edit_stock_part_only_changes_quantity(self):
        inv = Inventory.objects.create(
            user=self.user, switch=Switch.objects.create(stock=stock_switch())
        )
        context = self.modal_forms.edit_part_context(inv, '/edit', {'quantity': '45'})
        self.assertIsNone(context['form'])
        self.assertEqual(
            self.part_manager.edit_part(context, {'quantity': '45'}).quantity, 45
        )

    def test_edit_bad_quantity(self):
        inv = Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        data = {'quantity': '', 'kit-brand': 'KBDfans', 'kit-name': 'Tofu60'}
        context = self.modal_forms.edit_part_context(inv, '/edit', data)
        self.assertIsNone(self.part_manager.edit_part(context, data))
        self.assertEqual(context['quantity_error'], const.QUANTITY_ERROR)
        inv.kit.custom.refresh_from_db()
        self.assertEqual(inv.kit.custom.name, 'Tofu65')

    def test_delete_custom_part_removes_it(self):
        wrapper = custom_kit_wrapper()
        inv = Inventory.objects.create(user=self.user, kit=wrapper)
        self.part_manager.delete_part(inv)
        self.assertFalse(Inventory.objects.exists())
        self.assertFalse(CustomKit.objects.exists())

    def test_delete_stock_part_keeps_catalog(self):
        plate = stock_plate()
        inv = Inventory.objects.create(
            user=self.user, plate=Plate.objects.create(stock=plate)
        )
        self.part_manager.delete_part(inv)
        self.assertFalse(Inventory.objects.exists())
        plate.refresh_from_db()

    def test_standalone_part_is_scoped_to_user(self):
        inv = Inventory.objects.create(user=self.other, kit=custom_kit_wrapper())
        self.assertIsNone(self.part_manager.standalone_part(inv.pk))


class KeyboardFormContextTests(UserTestCase):
    def test_defaults_to_type_step(self):
        context = self.modal_forms.keyboard_form_context('/add')
        self.assertIsNone(context['step'])
        self.assertEqual(context['kind'], 'custom')
        self.assertFalse(context['editing'])

    def test_custom_kind_skips_to_first_part(self):
        context = self.modal_forms.keyboard_form_context('/add', kind='custom')
        self.assertEqual(context['step'], 'kit')
        self.assertEqual(context['kind'], 'custom')

    def test_prebuilt_kind_skips_to_picker(self):
        stock_keyboard()
        context = self.modal_forms.keyboard_form_context('/add', kind='prebuilt')
        self.assertEqual(context['step'], 'prebuilt')
        self.assertEqual(context['kind'], 'prebuilt')

    def test_prebuilt_kind_without_catalog_stays_on_type_step(self):
        context = self.modal_forms.keyboard_form_context('/add', kind='prebuilt')
        self.assertIsNone(context['step'])
        self.assertEqual(context['kind'], 'custom')

    def test_editing_prebuilt_preselects_its_stock_parts(self):
        stock_kb = stock_keyboard()
        context = self.modal_forms.keyboard_form_context('/edit', current=stock_kb)
        kit = next(p for p in context['parts'] if p['type'] == 'kit')
        self.assertTrue(context['from_prebuilt'])
        self.assertEqual(kit['source'], 'stock')
        self.assertEqual(kit['stock_id'], str(stock_kb.kit.pk))

    def kit_source(self, preferred):
        Profile.objects.update_or_create(
            user=self.user, defaults={'default_part_source': preferred}
        )
        context = ModalForms(self.user).keyboard_form_context('/add')
        return next(p for p in context['parts'] if p['type'] == 'kit')['source']

    def test_kit_source_follows_preference(self):
        stock_kit()
        self.part_manager.add_to_parts('kit', custom_kit_wrapper())
        self.assertEqual(self.kit_source('smart'), 'owned')
        self.assertEqual(self.kit_source('stock'), 'stock')
        self.assertEqual(self.kit_source('custom'), 'custom')

    def test_stock_preference_without_catalog_falls_back_to_custom(self):
        self.assertEqual(self.kit_source('stock'), 'custom')

    def test_optional_parts_still_skip(self):
        Profile.objects.create(user=self.user, default_part_source='stock')
        stock_switch()
        context = self.modal_forms.keyboard_form_context('/add')
        switch = next(p for p in context['parts'] if p['type'] == 'switch')
        self.assertEqual(switch['source'], 'none')

    def test_add_part_follows_preference(self):
        Profile.objects.create(user=self.user, default_part_source='custom')
        stock_switch()
        context = self.modal_forms.add_part_context()
        switch = next(p for p in context['parts'] if p['type'] == 'switch')
        self.assertEqual(switch['source'], 'custom')

    def test_switch_count_defaults_from_board(self):
        kb = custom_keyboard(self.user, switch=custom_switch_wrapper(), switch_count=60)
        context = self.modal_forms.keyboard_form_context('/edit', current=kb)
        switch = next(p for p in context['parts'] if p['type'] == 'switch')
        self.assertEqual(switch['count'], 60)


class AddPrebuiltTests(UserTestCase):
    def add(self, prebuilt_id, user=None):
        user = user or self.user
        data = {'kind': 'prebuilt', 'prebuilt': str(prebuilt_id)}
        context = ModalForms(user).keyboard_form_context('/add', data)
        return context, KeyboardManager(user).add_prebuilt(context, data)

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
        return context, self.kb_manager.add_custom(context, data)

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
        return context, self.kb_manager.edit_keyboard(inventory, context, data)

    def test_editing_prebuilt_makes_a_custom_build(self):
        stock_kb = prebuilt_in_inventory(self.user)
        inventory = self.kb_manager.keyboard_inventory(stock_kb.pk, True)
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
        inventory = self.kb_manager.keyboard_inventory(stock_kb.pk, True)
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
        inventory = self.kb_manager.keyboard_inventory(kb.pk, False)
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
        inventory = self.kb_manager.keyboard_inventory(kb.pk, False)
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
        inventory = self.kb_manager.keyboard_inventory(kb.pk, False)
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
        inventory = self.kb_manager.keyboard_inventory(kb.pk, False)
        context, result = self.edit(
            inventory, {'kit-source': 'custom', 'kit-brand': '', 'kit-name': ''}
        )
        self.assertIsNone(result)
        self.assertEqual(context['step'], 'kit')
        kb.kit.custom.refresh_from_db()
        self.assertEqual(kb.kit.custom.name, 'Tofu65')

    def test_keyboard_inventory_is_scoped_to_user(self):
        kb = custom_keyboard(self.other)
        self.assertIsNone(self.kb_manager.keyboard_inventory(kb.pk, False))


class DeleteKeyboardTests(UserTestCase):
    def test_delete_custom_keeps_checked_parts(self):
        kb = custom_keyboard(self.user, switch=custom_switch_wrapper(), switch_count=60)
        kit, switch = kb.kit, kb.switch
        self.kb_manager.delete_keyboard(
            self.kb_manager.keyboard_inventory(kb.pk, False), keep=['kit']
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
        self.kb_manager.delete_keyboard(
            self.kb_manager.keyboard_inventory(kb.pk, False), keep=['kit', 'switch']
        )
        self.assertEqual(
            Inventory.objects.get(user=self.user, switch=switch).quantity, 60
        )

    def test_delete_prebuilt_keeps_catalog(self):
        stock_kb = prebuilt_in_inventory(self.user)
        self.kb_manager.delete_keyboard(
            self.kb_manager.keyboard_inventory(stock_kb.pk, True), keep=['switch']
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
            for part in KeyboardManager.keyboard_delete_parts(stock_kb)
        }
        self.assertEqual(set(parts), {'kit', 'switch', 'plate'})
        self.assertTrue(parts['switch']['name'].endswith('×82'))
