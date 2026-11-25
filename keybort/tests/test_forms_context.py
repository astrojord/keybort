from boards import const
from boards.helpers.forms_context import ModalForms, parse_quantity
from boards.models import (
    Profile,
)

from .base import (
    UserTestCase,
    custom_keyboard,
    custom_kit_wrapper,
    custom_switch_wrapper,
    stock_keyboard,
    stock_kit,
    stock_switch,
)


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
        kit = next(p for p in context['parts'] if p.type == 'kit')
        self.assertTrue(context['from_prebuilt'])
        self.assertEqual(kit.source, 'stock')
        self.assertEqual(kit.stock_id, str(stock_kb.kit.pk))

    def kit_source(self, preferred):
        Profile.objects.update_or_create(
            user=self.user, defaults={'default_part_source': preferred}
        )
        context = ModalForms(self.user).keyboard_form_context('/add')
        return next(p for p in context['parts'] if p.type == 'kit').source

    def test_kit_source_follows_preference(self):
        stock_kit()
        self.part_service.add_to_parts('kit', custom_kit_wrapper())
        self.assertEqual(self.kit_source('smart'), 'owned')
        self.assertEqual(self.kit_source('stock'), 'stock')
        self.assertEqual(self.kit_source('custom'), 'custom')

    def test_stock_preference_without_catalog_falls_back_to_custom(self):
        self.assertEqual(self.kit_source('stock'), 'custom')

    def test_optional_parts_still_skip(self):
        Profile.objects.create(user=self.user, default_part_source='stock')
        stock_switch()
        context = self.modal_forms.keyboard_form_context('/add')
        switch = next(p for p in context['parts'] if p.type == 'switch')
        self.assertEqual(switch.source, 'none')

    def test_add_part_follows_preference(self):
        Profile.objects.create(user=self.user, default_part_source='custom')
        stock_switch()
        context = self.modal_forms.add_part_context()
        switch = next(p for p in context['parts'] if p.type == 'switch')
        self.assertEqual(switch.source, 'custom')

    def test_switch_count_defaults_from_board(self):
        kb = custom_keyboard(self.user, switch=custom_switch_wrapper(), switch_count=60)
        context = self.modal_forms.keyboard_form_context('/edit', current=kb)
        switch = next(p for p in context['parts'] if p.type == 'switch')
        self.assertEqual(switch.count, 60)


class PartChoiceValidateTests(UserTestCase):
    def switch_part(self, data):
        context = self.modal_forms.keyboard_form_context('/add', data)
        return context, next(p for p in context['parts'] if p.type == 'switch')

    def test_validate_returns_error_without_setting_it(self):
        data = {'switch-source': 'stock', 'switch-stock': '999999'}
        _, part = self.switch_part(data)
        choice, error = part.validate(data)
        self.assertIsNone(choice)
        self.assertIn('stock option', error)
        self.assertIsNone(part.error)

    def test_validate_returns_choice(self):
        switch = stock_switch()
        data = {'switch-source': 'stock', 'switch-stock': str(switch.pk)}
        _, part = self.switch_part(data)
        self.assertEqual(part.validate(data), (('stock', switch), None))

    def test_skipped_optional_part_has_no_choice_or_error(self):
        data = {'switch-source': 'none'}
        _, part = self.switch_part(data)
        self.assertEqual(part.validate(data), (None, None))

    def test_switch_count_error_lands_on_switch_step(self):
        switch = stock_switch()
        data = {
            'kit-source': 'stock',
            'kit-stock': str(stock_kit().pk),
            'switch-source': 'stock',
            'switch-stock': str(switch.pk),
            'switch-count': 'lots',
            'details-notes': '',
        }
        context, part = self.switch_part(data)
        submission = ModalForms.validate_parts(data, context, count_switches=True)
        self.assertEqual(submission.step, 'switch')
        self.assertIsNone(submission.switch_count)
        self.assertEqual(part.error, 'Enter how many switches are on the board.')
