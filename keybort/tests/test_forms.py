from django.test import SimpleTestCase

from boards.forms import (
    CustomKeyboardDetailsForm,
    CustomKitForm,
    CustomPlateForm,
    CustomSwitchForm,
)


class CustomPartFormTests(SimpleTestCase):
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
