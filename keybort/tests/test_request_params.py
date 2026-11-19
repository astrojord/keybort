from django.test import RequestFactory, SimpleTestCase

from boards.request_params import is_id, keyboard_params


class IsIdTests(SimpleTestCase):
    def test_accepts_decimal_strings(self):
        self.assertTrue(is_id('4'))
        self.assertTrue(is_id('9' * 18))

    def test_rejects_everything_else(self):
        for value in ('', 'abc', '-1', '1.5', '²', '9' * 19, '1' * 5000):
            with self.subTest(value=value):
                self.assertFalse(is_id(value))


class KeyboardParamsTests(SimpleTestCase):
    def params(self, **query):
        return keyboard_params(RequestFactory().get('/', query))

    def test_parses_id_and_stock(self):
        self.assertEqual(self.params(id='4', stock='1'), ('4', True))
        self.assertEqual(self.params(id='4', stock='0'), ('4', False))

    def test_rejects_missing_or_malformed(self):
        self.assertIsNone(self.params())
        self.assertIsNone(self.params(id='4'))
        self.assertIsNone(self.params(id='abc', stock='1'))
        self.assertIsNone(self.params(id='²', stock='1'))
        self.assertIsNone(self.params(id='4', stock='yes'))
