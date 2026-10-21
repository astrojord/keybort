from django.db import IntegrityError, transaction

from boards.models import (
    CustomKit,
    CustomPlate,
    Inventory,
    Keyboard,
    Kit,
    Plate,
    StockKit,
    Switch,
)

from .base import (
    UserTestCase,
    custom_kit_wrapper,
    stock_keyboard,
    stock_kit,
    stock_switch,
)


class WrapperObjTests(UserTestCase):
    def test_custom_wrapper_resolves_to_custom_part(self):
        wrapper = custom_kit_wrapper()
        self.assertIsInstance(wrapper.obj, CustomKit)
        self.assertFalse(wrapper.obj.stock)

    def test_stock_wrapper_resolves_to_stock_part(self):
        kit = stock_kit()
        wrapper = Kit.objects.create(stock=kit)
        self.assertEqual(wrapper.obj, kit)
        self.assertTrue(wrapper.obj.stock)

    def test_inventory_obj_follows_whichever_fk_is_set(self):
        switch = Switch.objects.create(stock=stock_switch())
        inv = Inventory.objects.create(user=self.user, switch=switch)
        self.assertEqual(inv.obj, switch.obj)

    def test_inventory_obj_for_keyboard_is_the_board(self):
        stock_kb = stock_keyboard()
        inv = Inventory.objects.create(
            user=self.user, keyboard=Keyboard.objects.create(stock=stock_kb)
        )
        self.assertEqual(inv.obj, stock_kb)


class StrTests(UserTestCase):
    def test_wrapper_str_marks_source(self):
        self.assertEqual(str(custom_kit_wrapper()), 'KBDfans Tofu65 (kit) (custom)')
        self.assertEqual(
            str(Kit.objects.create(stock=stock_kit())), 'Keychron Q1 (kit) (stock)'
        )

    def test_switch_str_uses_category_display(self):
        self.assertEqual(str(stock_switch()), 'Gateron Yellow (Linear, 50.0g)')

    def test_plate_str_describes_the_plate(self):
        self.assertEqual(
            str(CustomPlate(material='Brass', flex_cuts=True, half=True)),
            'Brass (flex) (half)',
        )
        self.assertEqual(str(CustomPlate()), 'Plate')

    def test_keyboard_str(self):
        stock_kb = stock_keyboard()
        self.assertEqual(
            str(Keyboard.objects.create(stock=stock_kb)), 'Keychron Q1 (stock)'
        )

    def test_stock_parts_are_custom_subclasses(self):
        self.assertTrue(issubclass(StockKit, CustomKit))


class ConstraintTests(UserTestCase):
    def assertRejected(self, create):
        with self.assertRaises(IntegrityError), transaction.atomic():
            create()

    def test_wrapper_needs_custom_or_stock(self):
        self.assertRejected(lambda: Plate.objects.create())

    def test_wrapper_cant_be_both(self):
        self.assertRejected(
            lambda: Kit.objects.create(
                custom=CustomKit.objects.create(), stock=stock_kit()
            )
        )

    def test_keyboard_needs_custom_or_stock(self):
        self.assertRejected(lambda: Keyboard.objects.create())

    def test_inventory_needs_something(self):
        self.assertRejected(lambda: Inventory.objects.create(user=self.user))

    def test_inventory_cant_hold_two_things(self):
        kit = custom_kit_wrapper()
        switch = Switch.objects.create(stock=stock_switch())
        self.assertRejected(
            lambda: Inventory.objects.create(user=self.user, kit=kit, switch=switch)
        )
