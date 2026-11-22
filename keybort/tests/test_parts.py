from boards.helpers.parts import board_switch_count
from boards.models import (
    CustomKeyboard,
)

from .base import (
    UserTestCase,
    custom_kit_wrapper,
    stock_keyboard,
)


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
