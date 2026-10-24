from django.core.files.uploadedfile import SimpleUploadedFile

from boards.handlers import (
    handle_canned_parts_upload,
    stock_csv_columns,
    stock_csv_template,
)
from boards.models import (
    StockKeycaps,
    StockKit,
    StockPlate,
    StockStabilizer,
    StockSwitch,
)

from .base import UserTestCase, stock_switch


def upload(*lines, header=None):
    header = header or ','.join(stock_csv_columns())
    content = '\n'.join([header, *lines]).encode('utf-8-sig')
    return handle_canned_parts_upload(SimpleUploadedFile('parts.csv', content))


def row(**values):
    return ','.join(values.get(name, '') for name in stock_csv_columns())


class StockCsvUploadTests(UserTestCase):
    def test_columns_cover_every_part_type(self):
        columns = stock_csv_columns()
        self.assertEqual(columns[0], 'type')
        for name in ('size', 'mount_type', 'category', 'peak_force', 'flex_cuts'):
            self.assertIn(name, columns)
        self.assertNotIn('quantity', columns)
        self.assertEqual(stock_csv_template().strip(), ','.join(columns))

    def test_imports_every_part_type_from_one_file(self):
        result = upload(
            row(type='kit', brand='Keychron', name='Q1', size='75%', total_keys='82'),
            row(
                type='Switches',
                brand='Gateron',
                name='Yellow',
                category='Linear',
                bottom_out_force='50',
                lubed='yes',
            ),
            row(type='keycaps', brand='GMK', name='Olivia', material='ABS'),
            row(type='Plate', material='Brass', flex_cuts='1'),
            row(type='stabilizer', brand='Durock', name='V2'),
        )

        self.assertEqual(result['errors'], [])
        self.assertEqual(
            result['created'],
            {'kit': 1, 'switch': 1, 'keycaps': 1, 'plate': 1, 'stabilizer': 1},
        )
        self.assertEqual(StockKit.objects.get().total_keys, 82)
        switch = StockSwitch.objects.get()
        self.assertEqual((switch.category, switch.stem), ('l', 'mx'))
        self.assertTrue(switch.lubed)
        self.assertFalse(switch.filmed)
        self.assertTrue(StockPlate.objects.get().flex_cuts)
        self.assertEqual(StockKeycaps.objects.count(), 1)
        self.assertEqual(StockStabilizer.objects.count(), 1)

    def test_header_can_be_a_subset_in_any_order(self):
        result = upload('Durock,V2,stabilizer', header='Brand,Name,Type')
        self.assertEqual(result['created']['stabilizer'], 1)

    def test_any_bad_row_rolls_back_the_whole_file(self):
        result = upload(
            row(type='kit', brand='Keychron', name='Q1'),
            row(type='switch', brand='Gateron', category='bouncy'),
            row(type='widget', brand='x'),
            row(type='plate', material='Brass', size='60%'),
        )

        lines = {line for line, _ in result['errors']}
        self.assertEqual(lines, {3, 4, 5})
        messages = ' '.join(message for _, message in result['errors'])
        self.assertIn('name', messages)
        self.assertIn('category', messages)
        self.assertIn('unknown type', messages)
        self.assertIn("size doesn't apply to plate", messages)
        self.assertFalse(StockKit.objects.exists())

    def test_bad_boolean_is_an_error(self):
        result = upload(row(type='plate', material='Brass', half='maybe'))
        self.assertEqual(len(result['errors']), 1)
        self.assertFalse(StockPlate.objects.exists())

    def test_unknown_or_missing_columns(self):
        result = upload('kit,Q1', header='type,colour')
        self.assertIn('colour', result['errors'][0][1])

        result = upload('Keychron,Q1', header='brand,name')
        self.assertIn('type', result['errors'][0][1])

    def test_skips_duplicates_already_stocked_or_repeated(self):
        stock_switch()
        result = upload(
            row(
                type='switch',
                brand='Gateron',
                name='Yellow',
                category='l',
                bottom_out_force='50',
            ),
            row(type='plate', material='Brass'),
            row(type='plate', material='Brass'),
        )

        self.assertEqual(result['skipped'], 2)
        self.assertEqual(result['created']['plate'], 1)
        self.assertEqual(StockSwitch.objects.count(), 1)

    def test_reuploading_same_file_creates_nothing(self):
        line = row(type='switch', brand='Akko', name='Lavender', category='t')
        upload(line)
        result = upload(line)
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(StockSwitch.objects.count(), 1)

    def test_blank_lines_and_ragged_rows(self):
        result = upload(row(type='plate', material='POM'), '', ',,,')
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['created']['plate'], 1)

        result = upload('plate,Brass,extra', header='type,material')
        self.assertIn('more values', result['errors'][0][1])

    def test_rejects_non_utf8(self):
        result = handle_canned_parts_upload(
            SimpleUploadedFile('parts.csv', 'type,brand\nkit,Ä'.encode('utf-16'))
        )
        self.assertIn('UTF-8', result['errors'][0][1])
