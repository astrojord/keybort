import json

from django.test import TestCase
from django.urls import reverse

from boards import const
from boards.models import CustomKit, Inventory, Profile, StockKeyboard, Switch

from .base import (
    ClientTestCase,
    custom_keyboard,
    custom_kit_wrapper,
    make_user,
    prebuilt_in_inventory,
    stock_keyboard,
    stock_switch,
)


class LoginRequiredTests(TestCase):
    def test_inventory_pages_redirect_to_login(self):
        for name in (
            'inventory_keyboards',
            'inventory_parts',
            'keyboard_add',
            'keyboard_edit',
            'keyboard_delete',
            'part_add',
            'part_edit',
            'part_delete',
            'part_quantity',
            'account',
        ):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/accounts/login'))

    def test_index_is_public(self):
        self.assertEqual(self.client.get(reverse('index')).status_code, 200)


class KeyboardsPageTests(ClientTestCase):
    def test_tabs_and_row_kinds(self):
        prebuilt_in_inventory(self.user)
        custom_keyboard(self.user)
        response = self.client.get(reverse('inventory_keyboards'))

        self.assertEqual(
            response.context['filters'], list(const.KEYBOARD_KINDS.items())
        )
        self.assertContains(response, 'data-filter=""')
        self.assertContains(response, 'data-filter="prebuilt"')
        self.assertContains(response, 'data-filter="custom"')
        self.assertContains(response, 'data-type="prebuilt"', count=1)
        self.assertContains(response, 'data-type="custom"', count=1)

    def test_only_own_keyboards(self):
        custom_keyboard(self.other)
        response = self.client.get(reverse('inventory_keyboards'))
        self.assertEqual(response.context['inventory'], [])


class AddKeyboardViewTests(ClientTestCase):
    def test_get_opens_on_tab_kind(self):
        stock_keyboard()
        cases = {'': None, 'prebuilt': 'prebuilt', 'custom': 'kit', 'bogus': None}
        for kind, step in cases.items():
            with self.subTest(kind=kind):
                response = self.client.get(reverse('keyboard_add'), {'kind': kind})
                self.assertTemplateUsed(response, 'partials/keyboard_modal.html')
                self.assertEqual(response.context['step'], step)

    def test_post_prebuilt_appends_row(self):
        stock_kb = stock_keyboard()
        response = self.client.post(
            reverse('keyboard_add'), {'kind': 'prebuilt', 'prebuilt': stock_kb.pk}
        )
        self.assertEqual(response['HX-Retarget'], '#table-keyboards tbody')
        self.assertEqual(response['HX-Reswap'], 'beforeend')
        self.assertEqual(response['HX-Trigger'], const.CLOSE_DIALOG_EVENT)
        self.assertContains(response, f'id="keyboard-stock-{stock_kb.pk}"')
        self.assertContains(response, 'data-type="prebuilt"')

    def test_post_custom_appends_row(self):
        data = {
            'kind': 'custom',
            'kit-source': 'custom',
            'kit-brand': 'KBDfans',
            'kit-name': 'Tofu65',
        }
        response = self.client.post(reverse('keyboard_add'), data)
        self.assertEqual(response['HX-Retarget'], '#table-keyboards tbody')
        self.assertContains(response, 'data-type="custom"')
        self.assertContains(response, 'KBDfans Tofu65')

    def test_post_invalid_rerenders_modal(self):
        response = self.client.post(
            reverse('keyboard_add'), {'kind': 'custom', 'kit-source': 'custom'}
        )
        self.assertTemplateUsed(response, 'partials/keyboard_modal.html')
        self.assertNotIn('HX-Retarget', response)
        self.assertEqual(response.context['step'], 'kit')

    def test_post_unknown_kind(self):
        self.assertEqual(
            self.client.post(reverse('keyboard_add'), {'kind': 'bogus'}).status_code,
            400,
        )


class EditKeyboardViewTests(ClientTestCase):
    def test_bad_params(self):
        self.assertEqual(
            self.client.get(
                reverse('keyboard_edit'), {'id': 'x', 'stock': '1'}
            ).status_code,
            400,
        )

    def test_someone_elses_keyboard(self):
        kb = custom_keyboard(self.other)
        self.assertEqual(
            self.client.get(
                reverse('keyboard_edit'), {'id': kb.pk, 'stock': 0}
            ).status_code,
            404,
        )

    def test_get(self):
        kb = custom_keyboard(self.user)
        response = self.client.get(reverse('keyboard_edit'), {'id': kb.pk, 'stock': 0})
        self.assertTrue(response.context['editing'])

    def test_post_prebuilt_swaps_row(self):
        stock_kb = prebuilt_in_inventory(self.user)
        url = f'{reverse("keyboard_edit")}?id={stock_kb.pk}&stock=1'
        data = {
            'kit-source': 'stock',
            'kit-stock': stock_kb.kit.pk,
            'switch-source': 'stock',
            'switch-stock': stock_kb.switch.pk,
            'switch-count': '82',
        }
        response = self.client.post(url, data)
        self.assertEqual(response['HX-Retarget'], f'#keyboard-stock-{stock_kb.pk}')
        self.assertEqual(response['HX-Reswap'], 'outerHTML')
        self.assertContains(response, 'data-type="custom"')


class DeleteKeyboardViewTests(ClientTestCase):
    def test_get_lists_parts(self):
        stock_kb = prebuilt_in_inventory(self.user)
        response = self.client.get(
            reverse('keyboard_delete'), {'id': stock_kb.pk, 'stock': 1}
        )
        self.assertEqual(
            {part['type'] for part in response.context['parts']}, {'kit', 'switch'}
        )

    def test_post_deletes_row(self):
        kb = custom_keyboard(self.user)
        kit = kb.kit
        url = f'{reverse("keyboard_delete")}?id={kb.pk}&stock=0'
        response = self.client.post(url, {'keep': ['kit']})
        self.assertEqual(response['HX-Retarget'], f'#keyboard-custom-{kb.pk}')
        self.assertEqual(response['HX-Reswap'], 'delete')
        self.assertTrue(Inventory.objects.filter(user=self.user, kit=kit).exists())

    def test_parts_start_checked_by_default(self):
        stock_kb = prebuilt_in_inventory(self.user)
        response = self.client.get(
            reverse('keyboard_delete'), {'id': stock_kb.pk, 'stock': 1}
        )
        self.assertContains(response, 'value="kit" checked')

    def test_parts_start_unchecked_when_preferred(self):
        Profile.objects.create(user=self.user, keep_parts_on_delete=False)
        stock_kb = prebuilt_in_inventory(self.user)
        response = self.client.get(
            reverse('keyboard_delete'), {'id': stock_kb.pk, 'stock': 1}
        )
        self.assertContains(response, 'value="kit">')
        self.assertNotContains(response, 'value="kit" checked')

    def test_someone_elses_keyboard(self):
        stock_kb = prebuilt_in_inventory(self.other)
        url = f'{reverse("keyboard_delete")}?id={stock_kb.pk}&stock=1'
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(StockKeyboard.objects.filter(pk=stock_kb.pk).exists())


class PartsPageTests(ClientTestCase):
    def test_lists_parts_with_type_filters(self):
        Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        response = self.client.get(reverse('inventory_parts'))
        self.assertEqual(response.context['filters'], list(const.PART_PLURALS.items()))
        self.assertContains(response, 'data-type="kit"', count=1)


class AddPartViewTests(ClientTestCase):
    def test_get_opens_on_type(self):
        self.assertEqual(
            self.client.get(reverse('part_add'), {'type': 'plate'}).context['step'],
            'plate',
        )
        self.assertIsNone(
            self.client.get(reverse('part_add'), {'type': 'bogus'}).context['step']
        )

    def test_post_appends_then_stacks(self):
        switch = stock_switch()
        data = {
            'type': 'switch',
            'switch-source': 'stock',
            'switch-stock': switch.pk,
            'quantity': '70',
        }
        response = self.client.post(reverse('part_add'), data)
        self.assertEqual(response['HX-Retarget'], '#table-parts tbody')
        self.assertEqual(response['HX-Reswap'], 'beforeend')

        response = self.client.post(reverse('part_add'), data)
        inv = Inventory.objects.get(user=self.user, switch__stock=switch)
        self.assertEqual(response['HX-Retarget'], f'#part-{inv.pk}')
        self.assertEqual(response['HX-Reswap'], 'outerHTML')
        self.assertEqual(inv.quantity, 140)

    def test_post_invalid_rerenders_modal(self):
        response = self.client.post(
            reverse('part_add'),
            {'type': 'kit', 'kit-source': 'custom', 'quantity': '1'},
        )
        self.assertTemplateUsed(response, 'partials/part_add_modal.html')
        self.assertNotIn('HX-Retarget', response)

    def test_post_unknown_type(self):
        self.assertEqual(
            self.client.post(reverse('part_add'), {'type': 'bogus'}).status_code, 400
        )


class EditDeletePartViewTests(ClientTestCase):
    def test_bad_id(self):
        for name in ('part_edit', 'part_delete'):
            with self.subTest(name=name):
                self.assertEqual(
                    self.client.get(reverse(name), {'id': 'x'}).status_code, 400
                )

    def test_someone_elses_part(self):
        inv = Inventory.objects.create(user=self.other, kit=custom_kit_wrapper())
        for name in ('part_edit', 'part_delete'):
            with self.subTest(name=name):
                self.assertEqual(
                    self.client.get(reverse(name), {'id': inv.pk}).status_code, 404
                )

    def test_edit_swaps_row(self):
        inv = Inventory.objects.create(
            user=self.user, switch=Switch.objects.create(stock=stock_switch())
        )
        response = self.client.post(
            f'{reverse("part_edit")}?id={inv.pk}', {'quantity': '12'}
        )
        self.assertEqual(response['HX-Retarget'], f'#part-{inv.pk}')
        inv.refresh_from_db()
        self.assertEqual(inv.quantity, 12)

    def test_delete_removes_row(self):
        inv = Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        response = self.client.post(f'{reverse("part_delete")}?id={inv.pk}')
        self.assertEqual(response['HX-Retarget'], f'#part-{inv.pk}')
        self.assertEqual(response['HX-Reswap'], 'delete')
        self.assertFalse(CustomKit.objects.exists())

    def test_htmx_delete_sends_toast(self):
        inv = Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        response = self.client.post(
            f'{reverse("part_delete")}?id={inv.pk}', headers={'HX-Request': 'true'}
        )
        trigger = json.loads(response['HX-Trigger'])
        self.assertIn(const.CLOSE_DIALOG_EVENT, trigger)
        self.assertEqual(trigger['messages'][0]['level'], 'success')
        self.assertIn('Removed', trigger['messages'][0]['message'])

    def test_htmx_missing_part_sends_error_toast(self):
        inv = Inventory.objects.create(user=self.other, kit=custom_kit_wrapper())
        response = self.client.get(
            reverse('part_edit'), {'id': inv.pk}, headers={'HX-Request': 'true'}
        )
        self.assertEqual(response.status_code, 404)
        trigger = json.loads(response['HX-Trigger'])
        self.assertEqual(trigger['messages'][0]['level'], 'error')


class PartQuantityViewTests(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.inv = Inventory.objects.create(
            user=self.user,
            switch=Switch.objects.create(stock=stock_switch()),
            quantity=70,
        )
        self.url = f'{reverse("part_quantity")}?id={self.inv.pk}'

    def post(self, quantity):
        return self.client.post(
            self.url, {'quantity': quantity}, headers={'HX-Request': 'true'}
        )

    def test_saves_and_returns_row(self):
        response = self.post('90')
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.quantity, 90)
        self.assertContains(response, f'id="part-{self.inv.pk}"')
        self.assertContains(response, 'value="90"')
        trigger = json.loads(response['HX-Trigger'])
        self.assertEqual(trigger['messages'][0]['level'], 'success')

    def test_invalid_keeps_quantity(self):
        for quantity in ('0', '-3', 'lots', ''):
            with self.subTest(quantity=quantity):
                response = self.post(quantity)
                self.inv.refresh_from_db()
                self.assertEqual(self.inv.quantity, 70)
                self.assertContains(response, 'value="70"')
                trigger = json.loads(response['HX-Trigger'])
                self.assertEqual(
                    trigger['messages'][0]['message'], const.QUANTITY_ERROR
                )

    def test_unchanged_sends_no_toast(self):
        response = self.post('70')
        self.assertNotIn('HX-Trigger', response)

    def test_get_and_bad_id(self):
        self.assertEqual(self.client.get(self.url).status_code, 400)
        response = self.client.post(reverse('part_quantity'), {'id': 'x'})
        self.assertEqual(response.status_code, 400)

    def test_someone_elses_part(self):
        inv = Inventory.objects.create(user=self.other, kit=custom_kit_wrapper())
        response = self.client.post(
            f'{reverse("part_quantity")}?id={inv.pk}', {'quantity': '5'}
        )
        self.assertEqual(response.status_code, 404)
        inv.refresh_from_db()
        self.assertEqual(inv.quantity, 1)


class PartDetailViewTests(TestCase):
    def test_stock_part_is_public(self):
        switch = stock_switch()
        response = self.client.get(
            reverse('part_detail'), {'type': 'switch', 'id': switch.pk, 'stock': 1}
        )
        self.assertEqual(response.context['part_title'], str(switch))
        self.assertEqual(response.context['fields']['Category'], 'Linear')

    def test_custom_part_is_private(self):
        kb = custom_keyboard(make_user('owner'))
        params = {'type': 'kit', 'id': kb.kit.custom_id, 'stock': 0}
        self.assertEqual(
            self.client.get(reverse('part_detail'), params).status_code, 404
        )

    def test_bad_params(self):
        for params in (
            {'type': 'bogus', 'id': 1, 'stock': 1},
            {'type': 'kit', 'id': 'x', 'stock': 1},
            {'type': 'kit', 'id': 1},
        ):
            with self.subTest(params=params):
                self.assertEqual(
                    self.client.get(reverse('part_detail'), params).status_code, 400
                )


class DashboardTests(ClientTestCase):
    def test_counts(self):
        prebuilt_in_inventory(self.user)
        custom_keyboard(self.user)
        custom_keyboard(self.other)
        self.manager.add_to_parts(
            'switch', Switch.objects.create(stock=stock_switch()), quantity=70
        )
        response = self.client.get(reverse('index'))

        self.assertEqual(response.context['keyboard_count'], 2)
        self.assertEqual(response.context['prebuilt_count'], 1)
        self.assertEqual(response.context['custom_count'], 1)
        self.assertEqual(response.context['part_entries'], 1)
        self.assertEqual(response.context['switches_loose'], 70)
        self.assertEqual(response.context['switches_on_boards'], 82)
        self.assertEqual(len(response.context['recent_keyboards']), 2)
        self.assertContains(response, '?add=custom')
        self.assertContains(response, '?add=switch')

    def test_empty_inventory(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.context['keyboard_count'], 0)
        self.assertEqual(response.context['recent_keyboards'], [])
        self.assertContains(response, 'No keyboards yet')


class AccountViewTests(ClientTestCase):
    def test_get_shows_defaults(self):
        custom_keyboard(self.user)
        response = self.client.get(reverse('account'))
        self.assertEqual(response.context['keyboard_count'], 1)
        self.assertContains(response, 'value="smart" required checked')
        self.assertContains(response, 'name="keep_parts_on_delete" checked')

    def test_htmx_post_saves_and_toasts(self):
        response = self.client.post(
            reverse('account'),
            {'default_part_source': 'stock'},
            headers={'HX-Request': 'true'},
        )
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.default_part_source, 'stock')
        self.assertFalse(profile.keep_parts_on_delete)
        self.assertTemplateUsed(response, 'partials/account_preferences.html')
        self.assertIn('Saved preferences.', response['HX-Trigger'])

    def test_invalid_post_keeps_saved_values(self):
        response = self.client.post(
            reverse('account'),
            {'default_part_source': 'bogus'},
            headers={'HX-Request': 'true'},
        )
        self.assertContains(response, "couldn't be saved")
        self.assertEqual(
            Profile.objects.get(user=self.user).default_part_source, 'smart'
        )


class AnonymousDashboardTests(TestCase):
    def test_landing_page(self):
        response = self.client.get(reverse('index'))
        self.assertNotIn('keyboard_count', response.context)
        self.assertContains(response, 'Sign in')


class OpenAddModalTests(ClientTestCase):
    def test_keyboards_page_opens_add_for_kind(self):
        response = self.client.get(reverse('inventory_keyboards') + '?add=custom')
        self.assertEqual(response.context['open_add'], 'custom')
        self.assertContains(response, 'hx-trigger="load"')

    def test_keyboards_page_ignores_unknown_kind(self):
        response = self.client.get(reverse('inventory_keyboards') + '?add=bogus')
        self.assertIsNone(response.context['open_add'])
        self.assertNotContains(response, 'hx-trigger="load"')

    def test_parts_page_opens_add_for_type(self):
        response = self.client.get(reverse('inventory_parts') + '?add=switch')
        self.assertEqual(response.context['open_add'], 'switch')
        self.assertContains(response, 'hx-trigger="load"')

    def test_parts_page_opens_type_picker(self):
        response = self.client.get(reverse('inventory_parts') + '?add=bogus')
        self.assertEqual(response.context['open_add'], '')
        self.assertContains(response, 'hx-trigger="load"')

    def test_parts_page_without_add(self):
        response = self.client.get(reverse('inventory_parts'))
        self.assertNotIn('open_add', response.context)
        self.assertNotContains(response, 'hx-trigger="load"')
