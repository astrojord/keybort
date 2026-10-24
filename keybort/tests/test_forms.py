from django.test import TestCase

from boards.forms import (
    ComboboxInput,
    CustomKeyboardDetailsForm,
    CustomKitForm,
    CustomPlateForm,
    CustomSwitchForm,
    StockKitForm,
)
from boards.models import CustomKit

from .base import stock_kit, stock_switch


class CustomPartFormTests(TestCase):
    def test_brand_and_name_required(self):
        form = CustomKitForm({})
        self.assertFalse(form.is_valid())
        self.assertIn('brand', form.errors)
        self.assertIn('name', form.errors)

    def test_valid_with_brand_and_name(self):
        self.assertTrue(
            CustomKitForm({'brand': 'KBDfans', 'name': 'Tofu65'}).is_valid()
        )

    def test_parts_without_brand_or_name_need_nothing(self):
        self.assertTrue(CustomPlateForm({}).is_valid())
        self.assertTrue(CustomKeyboardDetailsForm({}).is_valid())

    def test_switch_form_leaves_out_quantity(self):
        self.assertNotIn('quantity', CustomSwitchForm().fields)

    def test_textareas_are_short(self):
        self.assertEqual(CustomKitForm().fields['notes'].widget.attrs['rows'], 3)


class ComboboxTests(TestCase):
    def test_text_fields_stay_plain_without_stock_parts(self):
        self.assertNotIsInstance(CustomKitForm().fields['brand'].widget, ComboboxInput)

    def test_options_come_from_stock_parts(self):
        stock_kit(brand='Keychron', name='Q1')
        stock_kit(brand='Keychron', name='Q2')
        stock_kit(brand='KBDfans', name='Tofu65')
        CustomKit.objects.create(brand='Custom Co', name='Mine')

        widget = CustomKitForm().fields['brand'].widget
        self.assertIsInstance(widget, ComboboxInput)
        self.assertEqual(widget.options, ['KBDfans', 'Keychron'])

    def test_blank_stock_values_are_left_out(self):
        stock_kit(size='')
        stock_kit(size=None)
        self.assertNotIsInstance(CustomKitForm().fields['size'].widget, ComboboxInput)

        stock_kit(size='65%')
        self.assertEqual(CustomKitForm().fields['size'].widget.options, ['65%'])

    def test_options_are_per_part_type(self):
        stock_switch(brand='Gateron')
        self.assertEqual(CustomSwitchForm().fields['brand'].widget.options, ['Gateron'])
        self.assertNotIsInstance(CustomKitForm().fields['brand'].widget, ComboboxInput)

    def test_choice_fields_are_untouched(self):
        stock_switch()
        self.assertNotIsInstance(
            CustomSwitchForm().fields['category'].widget, ComboboxInput
        )

    def test_stock_forms_suggest_too(self):
        stock_kit(brand='Keychron')
        self.assertIsInstance(StockKitForm().fields['brand'].widget, ComboboxInput)

    def test_renders_free_text_input_with_options(self):
        stock_kit(brand='Keychron')
        html = str(CustomKitForm(prefix='kit', initial={'brand': 'Mode'})['brand'])
        self.assertIn('name="kit-brand"', html)
        self.assertIn('value="Mode"', html)
        self.assertIn('role="combobox"', html)
        self.assertIn('maxlength="255"', html)
        self.assertIn('required', html)
        self.assertIn('<div role="option" data-value="Keychron">Keychron</div>', html)

    def test_errors_point_at_field_error(self):
        stock_kit(brand='Keychron')
        html = str(CustomKitForm({}, prefix='kit')['brand'])
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="id_kit-brand-error"', html)
