from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from boards.models import CustomSwitch
from boards.utils import htmx_swap, keyboard_params, model_to_dict_verbose


class KeyboardParamsTests(SimpleTestCase):
    def params(self, **query):
        return keyboard_params(RequestFactory().get("/", query))

    def test_parses_id_and_stock(self):
        self.assertEqual(self.params(id="4", stock="1"), ("4", True))
        self.assertEqual(self.params(id="4", stock="0"), ("4", False))

    def test_rejects_missing_or_malformed(self):
        self.assertIsNone(self.params())
        self.assertIsNone(self.params(id="4"))
        self.assertIsNone(self.params(id="abc", stock="1"))
        self.assertIsNone(self.params(id="4", stock="yes"))


class HtmxSwapTests(SimpleTestCase):
    def test_sets_retarget_and_reswap(self):
        response = htmx_swap(HttpResponse(), "#row", "outerHTML")
        self.assertEqual(response["HX-Retarget"], "#row")
        self.assertEqual(response["HX-Reswap"], "outerHTML")
        self.assertNotIn("HX-Trigger", response)

    def test_sets_trigger_when_given(self):
        response = htmx_swap(HttpResponse(), "#row", "delete", "close-dialog")
        self.assertEqual(response["HX-Trigger"], "close-dialog")


class ModelToDictVerboseTests(SimpleTestCase):
    def test_uses_verbose_names_and_choice_labels(self):
        switch = CustomSwitch(brand="JWK", name="Alpaca", category="t", lubed=True)
        data = model_to_dict_verbose(switch, fields=["brand", "category", "lubed"])
        self.assertEqual(data, {"Brand": "JWK", "Category": "Tactile", "Lubed": True})

    def test_exclude(self):
        data = model_to_dict_verbose(CustomSwitch(brand="JWK"), exclude=["brand"])
        self.assertNotIn("Brand", data)
        self.assertIn("Name", data)

    def test_skips_unset_choice_fields(self):
        data = model_to_dict_verbose(CustomSwitch(), fields=["category"])
        self.assertEqual(data, {})
