from django.core.exceptions import BadRequest
from django.test import RequestFactory, SimpleTestCase

from boards.request_params import is_id, keyboard_params, require_id


def get(**query):
    return RequestFactory().get('/', query)


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
        return keyboard_params(get(**query))

    def test_parses_id_and_stock(self):
        self.assertEqual(self.params(id='4', stock='1'), ('4', True))
        self.assertEqual(self.params(id='4', stock='0'), ('4', False))

    def test_rejects_missing_or_malformed(self):
        for query in (
            {},
            {'id': '4'},
            {'id': 'abc', 'stock': '1'},
            {'id': '²', 'stock': '1'},
            {'id': '4', 'stock': 'yes'},
        ):
            with self.subTest(query=query), self.assertRaises(BadRequest):
                self.params(**query)


class RequireIdTests(SimpleTestCase):
    def test_returns_valid_id(self):
        self.assertEqual(require_id(get(id='12')), '12')
        self.assertEqual(require_id(get(kb='3'), name='kb'), '3')

    def test_rejects_missing_or_malformed(self):
        for query in ({}, {'id': ''}, {'id': 'x'}, {'id': '9' * 19}):
            with self.subTest(query=query), self.assertRaises(BadRequest):
                require_id(get(**query))
