from django.test import SimpleTestCase

from boards.helpers.parts import switch_kind
from boards.helpers.rows import (
    field_display,
    keyboard_ref,
    keyboard_row,
    model_to_dict_verbose,
    parse_keyboard_ref,
    part_cells,
    part_columns,
    part_info,
    part_row,
)
from boards.models import (
    CustomKit,
    CustomSwitch,
    Inventory,
)

from .base import (
    UserTestCase,
    custom_keyboard,
    custom_kit_wrapper,
    stock_keyboard,
)


class PartDisplayTests(UserTestCase):
    def test_keyboard_row_names_skip_blank_brand(self):
        kb = custom_keyboard(self.user, kit=custom_kit_wrapper(brand=None))
        self.assertEqual(keyboard_row(kb).kit.name, 'Tofu65')

    def test_switch_info(self):
        switch = CustomSwitch(
            category='t',
            bottom_out_force=62.0,
            top_housing='pc',
            lubed=True,
            notes='hand lubed',
        )
        self.assertEqual(
            part_info('switch', switch),
            'Tactile, 62gf, Polycarbonate top, lubed, hand lubed',
        )

    def test_switch_kind_maps_category(self):
        self.assertEqual(
            switch_kind(CustomSwitch(category='st')),
            {'slug': 'silent-tactile', 'label': 'Silent Tactile'},
        )
        self.assertIsNone(switch_kind(CustomSwitch()))
        self.assertIsNone(switch_kind(None))

    def test_kit_info(self):
        kit = CustomKit(size='65%', pcb='Hotswap')
        self.assertEqual(part_info('kit', kit), '65%, Hotswap PCB')

    def test_part_row(self):
        inv = Inventory.objects.create(
            user=self.user, kit=custom_kit_wrapper(), quantity=2
        )
        row = part_row(inv)
        self.assertEqual(row.row_id, f'part-{inv.pk}')
        self.assertEqual(row.type, 'kit')
        self.assertEqual(row.name, 'KBDfans Tofu65')
        self.assertEqual(row.quantity, 2)
        self.assertFalse(row.is_stock)

    def test_part_columns_have_unique_sort_keys(self):
        keys = [column['key'] for column in part_columns()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_part_columns_label_each_field(self):
        columns = part_columns()
        labels = {column['key']: column['label'] for column in columns}
        self.assertEqual(labels['switch-stem'], 'Stem')
        self.assertEqual(labels['switch-category'], 'Type')
        self.assertEqual(labels['plate-half'], 'Half plate')

    def test_part_cells_line_up_with_columns(self):
        switch = CustomSwitch(
            stem='mx', peak_force=45.0, lubed=True, notes='hand lubed'
        )
        cells = part_cells('switch', switch)
        columns = part_columns()
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
        cells = part_cells('switch', switch)
        columns = part_columns()
        flags = {
            column['key']: cell['flag']
            for column, cell in zip(columns, cells, strict=True)
            if cell['flag'] is not None
        }
        self.assertEqual(flags, {'switch-lubed': True, 'switch-filmed': False})

    def test_travel_column_label(self):
        labels = {c['key']: c['label'] for c in part_columns()}
        self.assertEqual(labels['switch-travel_distance'], 'Travel')

    def test_force_combines_peak_then_bottom_out(self):
        switch = CustomSwitch(peak_force=55.0, bottom_out_force=65.0)
        self.assertEqual(field_display(switch, 'force'), '55gf / 65gf')

    def test_housing_combines_top_and_bottom(self):
        switch = CustomSwitch(top_housing='pc', bottom_housing='nylon')
        self.assertEqual(field_display(switch, 'housing'), 'Polycarbonate / Nylon')

    def test_housing_marks_missing_side(self):
        switch = CustomSwitch(top_housing='pom')
        self.assertEqual(field_display(switch, 'housing'), 'POM / —')

    def test_housing_blank_when_unset(self):
        self.assertEqual(field_display(CustomSwitch(), 'housing'), '')

    def test_part_cells_blank_for_other_types(self):
        cells = part_cells('switch', CustomSwitch(notes='hand lubed'))
        other_values = {cell['value'] for cell in cells if cell['type'] != 'switch'}
        self.assertEqual(other_values, {''})


class KeyboardRefTests(UserTestCase):
    def test_round_trips(self):
        stock_kb = stock_keyboard()
        kb = custom_keyboard(self.user)
        self.assertEqual(
            parse_keyboard_ref(keyboard_ref(stock_kb)), (str(stock_kb.pk), True)
        )
        self.assertEqual(parse_keyboard_ref(keyboard_ref(kb)), (str(kb.pk), False))

    def test_rejects_malformed(self):
        for ref in ('', '4', 'stock-', 'stock-x', 'prebuilt-4', '-4', 'custom-4-5'):
            with self.subTest(ref=ref):
                self.assertIsNone(parse_keyboard_ref(ref))


class ModelToDictVerboseTests(SimpleTestCase):
    def test_uses_verbose_names_and_choice_labels(self):
        switch = CustomSwitch(brand='JWK', name='Alpaca', category='t', lubed=True)
        data = model_to_dict_verbose(switch, fields=['brand', 'category', 'lubed'])
        self.assertEqual(data, {'Brand': 'JWK', 'Category': 'Tactile', 'Lubed': True})

    def test_exclude(self):
        data = model_to_dict_verbose(CustomSwitch(brand='JWK'), exclude=['brand'])
        self.assertNotIn('Brand', data)
        self.assertIn('Name', data)

    def test_skips_unset_choice_fields(self):
        data = model_to_dict_verbose(CustomSwitch(), fields=['category'])
        self.assertEqual(data, {})
