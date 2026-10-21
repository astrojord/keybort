from django.contrib.auth.models import User
from django.test import TestCase

from boards.managers import KeyboardManager
from boards.models import (
    CustomKeyboard,
    CustomKit,
    CustomSwitch,
    Inventory,
    Keyboard,
    Kit,
    StockKeyboard,
    StockKeycaps,
    StockKit,
    StockPlate,
    StockStabilizer,
    StockSwitch,
    Switch,
)


def make_user(username='jordan'):
    return User.objects.create_user(username=username, password='pw')


def stock_kit(**fields):
    return StockKit.objects.create(
        **{
            'brand': 'Keychron',
            'name': 'Q1',
            'total_keys': 82,
            'pcb': 'Hotswap',
            **fields,
        }
    )


def stock_switch(**fields):
    return StockSwitch.objects.create(
        **{
            'brand': 'Gateron',
            'name': 'Yellow',
            'category': 'l',
            'bottom_out_force': 50.0,
            **fields,
        }
    )


def stock_keycaps(**fields):
    return StockKeycaps.objects.create(
        **{'brand': 'GMK', 'name': 'Olivia', 'material': 'ABS', **fields}
    )


def stock_plate(**fields):
    return StockPlate.objects.create(**{'material': 'Aluminum', **fields})


def stock_stabilizer(**fields):
    return StockStabilizer.objects.create(**{'brand': 'Durock', 'name': 'V2', **fields})


def stock_keyboard(**fields):
    defaults = {'kit': stock_kit(), 'switch': stock_switch()}
    return StockKeyboard.objects.create(**{**defaults, **fields})


def custom_kit_wrapper(**fields):
    return Kit.objects.create(
        custom=CustomKit.objects.create(
            **{'brand': 'KBDfans', 'name': 'Tofu65', **fields}
        )
    )


def custom_switch_wrapper(**fields):
    return Switch.objects.create(
        custom=CustomSwitch.objects.create(
            **{'brand': 'JWK', 'name': 'Alpaca', 'category': 'l', **fields}
        )
    )


def custom_keyboard(user, **fields):
    kb = CustomKeyboard.objects.create(**{'kit': custom_kit_wrapper(), **fields})
    Inventory.objects.create(user=user, keyboard=Keyboard.objects.create(custom=kb))
    return kb


def prebuilt_in_inventory(user, stock_kb=None):
    stock_kb = stock_kb or stock_keyboard()
    keyboard, _ = Keyboard.objects.get_or_create(stock=stock_kb)
    Inventory.objects.create(user=user, keyboard=keyboard)
    return stock_kb


class UserTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.other = make_user('someone-else')

    def setUp(self):
        self.manager = KeyboardManager(self.user)


class ClientTestCase(UserTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
