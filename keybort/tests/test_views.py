import json

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from boards import const
from boards.managers import KeyboardManager
from boards.models import (
    CustomKit,
    Inventory,
    Kit,
    Profile,
    StockKeyboard,
    StockKeycaps,
    StockKit,
    StockSwitch,
    Switch,
)

from .base import (
    ClientTestCase,
    custom_keyboard,
    custom_kit_wrapper,
    make_user,
    prebuilt_in_inventory,
    stock_keyboard,
    stock_keycaps,
    stock_kit,
    stock_plate,
    stock_stabilizer,
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

    def test_get_starts_on_requested_step(self):
        kb = custom_keyboard(self.user)
        url = reverse('keyboard_edit')
        response = self.client.get(url, {'id': kb.pk, 'stock': 0, 'step': 'keycaps'})
        self.assertEqual(response.context['step'], 'keycaps')
        response = self.client.get(url, {'id': kb.pk, 'stock': 0, 'step': 'bogus'})
        self.assertIsNone(response.context['step'])

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
    def test_single_lists_parts(self):
        stock_kb = prebuilt_in_inventory(self.user)
        response = self.client.get(
            reverse('keyboard_delete'), {'ids': f'stock-{stock_kb.pk}'}
        )
        self.assertEqual(
            {part['type'] for part in response.context['parts']}, {'kit', 'switch'}
        )
        self.assertNotIn('reminder', response.context)

    def test_single_keeps_chosen_parts(self):
        kb = custom_keyboard(self.user)
        kit = kb.kit
        response = self.client.post(
            reverse('keyboard_delete'), {'ids': f'custom-{kb.pk}', 'keep': ['kit']}
        )
        triggers = json.loads(response['HX-Trigger'])
        self.assertEqual(triggers['rows-deleted']['ids'], [f'keyboard-custom-{kb.pk}'])
        self.assertTrue(Inventory.objects.filter(user=self.user, kit=kit).exists())

    def test_parts_start_checked_by_default(self):
        stock_kb = prebuilt_in_inventory(self.user)
        response = self.client.get(
            reverse('keyboard_delete'), {'ids': f'stock-{stock_kb.pk}'}
        )
        self.assertContains(response, 'value="kit" checked')

    def test_parts_start_unchecked_when_preferred(self):
        Profile.objects.create(user=self.user, keep_parts_on_delete=False)
        stock_kb = prebuilt_in_inventory(self.user)
        response = self.client.get(
            reverse('keyboard_delete'), {'ids': f'stock-{stock_kb.pk}'}
        )
        self.assertContains(response, 'value="kit">')
        self.assertNotContains(response, 'value="kit" checked')

    def test_multiple_drop_parts_with_reminder(self):
        prebuilt = prebuilt_in_inventory(self.user)
        build = custom_keyboard(self.user)
        ids = [f'stock-{prebuilt.pk}', f'custom-{build.pk}']
        url = reverse('keyboard_delete')

        response = self.client.get(url, {'ids': ids})
        self.assertNotIn('parts', response.context)
        self.assertContains(response, 'edit popup')

        response = self.client.post(url, {'ids': ids, 'keep': ['kit', 'switch']})
        triggers = json.loads(response['HX-Trigger'])
        self.assertEqual(
            sorted(triggers['rows-deleted']['ids']),
            sorted([f'keyboard-stock-{prebuilt.pk}', f'keyboard-custom-{build.pk}']),
        )
        self.assertFalse(Inventory.objects.filter(user=self.user).exists())

    def test_someone_elses_keyboard(self):
        stock_kb = prebuilt_in_inventory(self.other)
        response = self.client.post(
            reverse('keyboard_delete'), {'ids': f'stock-{stock_kb.pk}'}
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Inventory.objects.filter(user=self.other).exists())

    def test_edit_popup_has_delete(self):
        kb = custom_keyboard(self.user)
        response = self.client.get(reverse('keyboard_edit'), {'id': kb.pk, 'stock': 0})
        self.assertEqual(
            response.context['delete_url'],
            f'{reverse("keyboard_delete")}?ids=custom-{kb.pk}',
        )
        self.assertContains(response, response.context['delete_url'])


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
        self.assertEqual(
            self.client.get(reverse('part_edit'), {'id': 'x'}).status_code, 400
        )
        self.assertEqual(
            self.client.get(reverse('part_delete'), {'ids': 'x'}).status_code, 400
        )

    def test_someone_elses_part(self):
        inv = Inventory.objects.create(user=self.other, kit=custom_kit_wrapper())
        self.assertEqual(
            self.client.get(reverse('part_edit'), {'id': inv.pk}).status_code, 404
        )
        self.assertEqual(
            self.client.post(reverse('part_delete'), {'ids': inv.pk}).status_code, 400
        )
        self.assertTrue(Inventory.objects.filter(pk=inv.pk).exists())

    def test_edit_popup_has_delete(self):
        inv = Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        response = self.client.get(reverse('part_edit'), {'id': inv.pk})
        self.assertContains(response, f'{reverse("part_delete")}?ids={inv.pk}')

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
        response = self.client.post(reverse('part_delete'), {'ids': inv.pk})
        triggers = json.loads(response['HX-Trigger'])
        self.assertEqual(triggers['rows-deleted']['ids'], [f'part-{inv.pk}'])
        self.assertFalse(CustomKit.objects.exists())

    def test_htmx_delete_sends_toast(self):
        inv = Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        response = self.client.post(
            reverse('part_delete'), {'ids': inv.pk}, headers={'HX-Request': 'true'}
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
        self.assertEqual(response.context['name'], f'{switch.brand} {switch.name}')
        self.assertEqual(response.context['type_label'], 'Switch')
        self.assertEqual(response.context['fields']['Category'], 'Linear')
        self.assertIsNone(response.context['edit_url'])

    def test_edit_url_only_points_at_edit_views(self):
        switch = stock_switch()
        base = {'type': 'switch', 'id': switch.pk, 'stock': 1}
        for edit, expected in (
            (f'{reverse("part_edit")}?id=3', f'{reverse("part_edit")}?id=3'),
            (
                f'{reverse("keyboard_edit")}?id=1&stock=0&step=kit',
                f'{reverse("keyboard_edit")}?id=1&stock=0&step=kit',
            ),
            (reverse('part_delete'), None),
            ('https://example.com/', None),
            (f'//example.com{reverse("part_edit")}', None),
            ('/nowhere', None),
        ):
            with self.subTest(edit=edit):
                response = self.client.get(
                    reverse('part_detail'), {**base, 'edit': edit}
                )
                self.assertEqual(response.context['edit_url'], expected)

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
        self.assertEqual(response.context['part_units'], 70)
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


class StockPrebuiltsPageTests(ClientTestCase):
    def test_lists_catalog_with_owned_flag(self):
        owned = prebuilt_in_inventory(self.user)
        other = stock_keyboard(kit=stock_kit(brand='Logitech', name='G915'))
        response = self.client.get(reverse('stock_prebuilts'))

        rows = {row['id']: row for row in response.context['prebuilts']}
        self.assertTrue(rows[owned.pk]['owned'])
        self.assertFalse(rows[other.pk]['owned'])
        self.assertContains(response, 'In inventory', count=1)
        self.assertContains(response, reverse('stock_prebuilt_collect'), count=1)
        self.assertNotContains(response, reverse('stock_prebuilt_add'))

    def test_facets_come_from_catalog_and_keep_url_selection(self):
        stock_keyboard(kit=stock_kit(brand='logitech', name='G915', size='TKL'))
        stock_keyboard(kit=stock_kit(size='75%', layout='ANSI'), bluetooth=True)
        response = self.client.get(
            reverse('stock_prebuilts'),
            {'brand': 'Keychron', 'connectivity': ['Wired', 'Bogus'], 'q': 'q1'},
        )

        facets = {
            facet['key']: facet['options'] for facet in response.context['facets']
        }
        self.assertEqual(facets['brand'], [('Keychron', True), ('logitech', False)])
        self.assertEqual(facets['size'], [('75%', False), ('TKL', False)])
        self.assertEqual(facets['layout'], [('ANSI', False)])
        self.assertEqual(
            facets['connectivity'],
            [('Wired', True), ('Wireless', False), ('Bluetooth', False)],
        )
        self.assertContains(response, 'value="q1"')
        self.assertContains(response, 'data-facet-connectivity="Bluetooth"')
        self.assertContains(response, 'data-facet-connectivity="Wired"')

    def test_connectivity_facet_lists_each_mode(self):
        row = KeyboardManager.stock_prebuilt_row(
            stock_keyboard(wireless=True, bluetooth=True)
        )
        self.assertEqual(row['facets']['connectivity'], ['Wireless', 'Bluetooth'])
        self.assertEqual(row['connectivity'], 'Wireless, Bluetooth')

    def test_public_without_actions(self):
        self.client.logout()
        stock_keyboard()
        response = self.client.get(reverse('stock_prebuilts'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('stock_prebuilt_collect'))

    def test_permissions_show_catalog_actions(self):
        stock_keyboard()
        for codename, url_name in (
            ('can_upload_stock_data', 'stock_prebuilt_add'),
            ('can_edit_stock_data', 'stock_prebuilt_edit'),
            ('can_delete_stock_data', 'stock_prebuilt_delete'),
        ):
            with self.subTest(codename=codename):
                self.assertNotContains(
                    self.client.get(reverse('stock_prebuilts')), reverse(url_name)
                )
                user = make_user(codename)
                grant(user, codename)
                self.client.force_login(user)
                self.assertContains(
                    self.client.get(reverse('stock_prebuilts')), reverse(url_name)
                )
                self.client.force_login(self.user)


class CollectStockPrebuiltViewTests(ClientTestCase):
    def test_adds_to_inventory_once(self):
        stock_kb = stock_keyboard()
        url = f'{reverse("stock_prebuilt_collect")}?id={stock_kb.pk}'
        for _ in range(2):
            response = self.client.post(url)
            self.assertTemplateUsed(response, 'partials/stock_prebuilt_row.html')
            self.assertTrue(response.context['kb']['owned'])
        self.assertEqual(
            Inventory.objects.filter(user=self.user, keyboard__stock=stock_kb).count(),
            1,
        )

    def test_bad_requests(self):
        url = reverse('stock_prebuilt_collect')
        self.assertEqual(self.client.get(f'{url}?id=1').status_code, 400)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertEqual(self.client.post(f'{url}?id=999').status_code, 404)

    def test_login_required(self):
        self.client.logout()
        response = self.client.post(f'{reverse("stock_prebuilt_collect")}?id=1')
        self.assertEqual(response.status_code, 302)


def grant(user, codename):
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label='boards', codename=codename)
    )


class AddStockPrebuiltViewTests(ClientTestCase):
    def setUp(self):
        super().setUp()
        uploader = make_user('uploader')
        grant(uploader, 'can_upload_stock_data')
        self.client.force_login(uploader)

    def test_without_permission_forbidden(self):
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(reverse('stock_prebuilt_add')).status_code, 403
        )
        self.assertEqual(
            self.client.post(reverse('stock_prebuilt_add')).status_code, 403
        )
        self.assertFalse(StockKeyboard.objects.exists())

    def test_post_with_stock_parts(self):
        kit = stock_kit()
        switch = stock_switch()
        response = self.client.post(
            reverse('stock_prebuilt_add'),
            {
                'kit-source': 'stock',
                'kit-stock': kit.pk,
                'switch-source': 'stock',
                'switch-stock': switch.pk,
                'keycaps-source': 'none',
                'plate-source': 'none',
                'stabilizer-source': 'none',
                'details-wireless': 'on',
            },
        )
        self.assertEqual(response['HX-Retarget'], '#table-prebuilts tbody')
        stock_kb = StockKeyboard.objects.get()
        self.assertEqual((stock_kb.kit, stock_kb.switch), (kit, switch))
        self.assertTrue(stock_kb.wireless)

    def test_post_with_new_kit_adds_it_to_catalog(self):
        self.client.post(
            reverse('stock_prebuilt_add'),
            {
                'kit-source': 'custom',
                'kit-brand': 'Razer',
                'kit-name': 'Huntsman',
                'switch-source': 'none',
                'keycaps-source': 'none',
                'plate-source': 'none',
                'stabilizer-source': 'none',
            },
        )
        stock_kb = StockKeyboard.objects.get()
        self.assertIsInstance(stock_kb.kit, StockKit)
        self.assertEqual(str(stock_kb), 'Razer Huntsman')
        self.assertFalse(CustomKit.objects.exclude(stockkit__isnull=False).exists())

    def test_post_invalid_rerenders_on_kit(self):
        response = self.client.post(
            reverse('stock_prebuilt_add'), {'kit-source': 'stock'}
        )
        self.assertTemplateUsed(response, 'partials/stock_prebuilt_modal.html')
        self.assertEqual(response.context['step'], 'kit')
        self.assertFalse(StockKeyboard.objects.exists())


class EditStockPrebuiltViewTests(ClientTestCase):
    def setUp(self):
        super().setUp()
        editor = make_user('editor')
        grant(editor, 'can_edit_stock_data')
        self.client.force_login(editor)
        self.stock_kb = stock_keyboard()
        self.url = f'{reverse("stock_prebuilt_edit")}?id={self.stock_kb.pk}'

    def post(self, **fields):
        return self.client.post(
            self.url,
            {
                'kit-source': 'stock',
                'kit-stock': self.stock_kb.kit.pk,
                'switch-source': 'none',
                'keycaps-source': 'none',
                'plate-source': 'none',
                'stabilizer-source': 'none',
                **fields,
            },
        )

    def test_without_permission_forbidden(self):
        uploader = make_user('uploader')
        grant(uploader, 'can_upload_stock_data')
        for user in (self.user, uploader):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, 403)
                self.assertEqual(self.post().status_code, 403)

    def test_get_prefills_current(self):
        response = self.client.get(self.url)
        self.assertTrue(response.context['editing'])
        parts = {part['type']: part for part in response.context['parts']}
        self.assertEqual(parts['kit']['source'], 'stock')
        self.assertEqual(parts['switch']['stock_id'], str(self.stock_kb.switch.pk))
        self.assertEqual(parts['keycaps']['source'], 'none')
        self.assertNotContains(response, 'data-removal')

    def test_post_saves_and_swaps_row(self):
        response = self.post(**{'details-bluetooth': 'on', 'details-notes': 'hi'})
        self.assertEqual(response['HX-Retarget'], f'#prebuilt-{self.stock_kb.pk}')
        self.assertEqual(response['HX-Reswap'], 'outerHTML')
        self.stock_kb.refresh_from_db()
        self.assertIsNone(self.stock_kb.switch)
        self.assertTrue(self.stock_kb.bluetooth)
        self.assertEqual(self.stock_kb.notes, 'hi')
        self.assertEqual(StockKeyboard.objects.count(), 1)

    def test_owners_keep_it(self):
        prebuilt_in_inventory(self.user, self.stock_kb)
        self.post(**{'details-wireless': 'on'})
        self.assertTrue(Inventory.objects.get(user=self.user).keyboard.obj.wireless)

    def test_bad_params(self):
        url = reverse('stock_prebuilt_edit')
        self.assertEqual(self.client.get(url).status_code, 400)
        self.assertEqual(self.client.get(f'{url}?id=999').status_code, 404)

    def test_post_invalid_rerenders(self):
        response = self.post(**{'kit-stock': ''})
        self.assertTemplateUsed(response, 'partials/stock_prebuilt_modal.html')
        self.assertEqual(response.context['step'], 'kit')


class DeleteStockPrebuiltViewTests(ClientTestCase):
    def setUp(self):
        super().setUp()
        deleter = make_user('deleter')
        grant(deleter, 'can_delete_stock_data')
        self.client.force_login(deleter)
        self.stock_kb = stock_keyboard(notes='catalog notes', wireless=True)
        self.url = f'{reverse("stock_prebuilt_delete")}?ids={self.stock_kb.pk}'

    def test_without_permission_forbidden(self):
        editor = make_user('editor')
        grant(editor, 'can_edit_stock_data')
        for user in (self.user, editor):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, 403)
                self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertTrue(StockKeyboard.objects.exists())

    def test_get_counts_owners(self):
        prebuilt_in_inventory(self.user, self.stock_kb)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'partials/delete_modal.html')
        self.assertIn('1 user has it', response.context['description'])

    def test_post_removes_row(self):
        response = self.client.post(self.url)
        triggers = json.loads(response['HX-Trigger'])
        self.assertEqual(
            triggers['rows-deleted']['ids'], [f'prebuilt-{self.stock_kb.pk}']
        )
        self.assertFalse(StockKeyboard.objects.exists())

    def test_owners_copies_become_custom_builds(self):
        kit, switch = self.stock_kb.kit, self.stock_kb.switch
        prebuilt_in_inventory(self.user, self.stock_kb)
        prebuilt_in_inventory(self.other, self.stock_kb)
        self.client.post(self.url)

        builds = [
            Inventory.objects.get(user=user).keyboard.obj
            for user in (self.user, self.other)
        ]
        self.assertNotEqual(builds[0].pk, builds[1].pk)
        for kb in builds:
            self.assertFalse(kb.stock)
            self.assertEqual((kb.kit.stock, kb.switch.stock), (kit, switch))
            self.assertEqual(kb.notes, 'catalog notes')
            self.assertTrue(kb.wireless)
        self.assertTrue(StockKit.objects.filter(pk=kit.pk).exists())

    def test_bad_params(self):
        url = reverse('stock_prebuilt_delete')
        self.assertEqual(self.client.get(url).status_code, 400)
        self.assertEqual(self.client.get(f'{url}?ids=999').status_code, 400)


class StockPartsPageTests(ClientTestCase):
    def test_each_stub_page_lists_its_catalog(self):
        cases = {
            'stock_kits': ('kit', stock_kit),
            'stock_switches': ('switch', stock_switch),
            'stock_keycaps': ('keycaps', stock_keycaps),
            'stock_plates': ('plate', stock_plate),
            'stock_stabilizers': ('stabilizer', stock_stabilizer),
        }
        for url_name, (part_type, factory) in cases.items():
            with self.subTest(url_name=url_name):
                obj = factory()
                response = self.client.get(reverse(url_name))
                self.assertTemplateUsed(response, 'pages/stock_parts.html')
                self.assertEqual(response.context['part_type'], part_type)
                self.assertEqual(
                    [row['id'] for row in response.context['parts']], [obj.pk]
                )

    def test_switch_columns_and_facets(self):
        stock_switch(stem='mx', top_housing='pc', travel_distance=4.0)
        stock_switch(brand='Akko', name='Jelly', category='t')
        response = self.client.get(reverse('stock_switches'), {'category': 'Tactile'})

        self.assertEqual(
            [label for _, label in response.context['columns']],
            [
                'Type',
                'Stem',
                'Bottom out force',
                'Travel distance',
                'Top housing',
                'Bottom housing',
            ],
        )
        facets = {
            facet['key']: facet['options'] for facet in response.context['facets']
        }
        self.assertEqual(facets['brand'], [('Akko', False), ('Gateron', False)])
        self.assertEqual(facets['category'], [('Linear', False), ('Tactile', True)])
        self.assertEqual(facets['top_housing'], [('Polycarbonate', False)])
        gateron = next(
            row for row in response.context['parts'] if row['name'] == 'Gateron Yellow'
        )
        self.assertEqual(
            gateron['columns'], ['Linear', 'MX', '50gf', '4mm', 'Polycarbonate', '']
        )

    def test_plate_boolean_facets(self):
        stock_plate(flex_cuts=True)
        response = self.client.get(reverse('stock_plates'))
        facets = {facet['key']: facet for facet in response.context['facets']}
        self.assertEqual(facets['flex_cuts']['options'], [('Yes', False)])
        self.assertEqual(facets['half']['label'], 'Half plate')
        self.assertContains(response, 'data-facet-flex_cuts="Yes"')

    def test_shows_quantity_in_parts(self):
        switch = stock_switch()
        self.manager.collect_stock_part('switch', switch, 70)
        response = self.client.get(reverse('stock_switches'))
        self.assertEqual(response.context['parts'][0]['quantity'], 70)
        self.assertContains(response, '70 in parts')

    def test_public_without_actions(self):
        self.client.logout()
        stock_switch()
        response = self.client.get(reverse('stock_switches'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('stock_part_collect'))

    def test_permissions_show_catalog_actions(self):
        stock_switch()
        for codename, url_name in (
            ('can_upload_stock_data', 'stock_part_add'),
            ('can_edit_stock_data', 'stock_part_edit'),
            ('can_delete_stock_data', 'stock_part_delete'),
        ):
            with self.subTest(codename=codename):
                self.assertNotContains(
                    self.client.get(reverse('stock_switches')), reverse(url_name)
                )
                user = make_user(codename)
                grant(user, codename)
                self.client.force_login(user)
                self.assertContains(
                    self.client.get(reverse('stock_switches')), reverse(url_name)
                )
                self.client.force_login(self.user)


class CollectStockPartViewTests(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.switch = stock_switch()
        self.url = f'{reverse("stock_part_collect")}?type=switch&id={self.switch.pk}'

    def test_get_modal(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'partials/stock_part_collect_modal.html')

    def test_post_adds_then_stacks(self):
        response = self.client.post(self.url, {'quantity': '70'})
        self.assertEqual(response['HX-Retarget'], f'#stock-switch-{self.switch.pk}')
        self.assertEqual(response.context['part']['quantity'], 70)
        response = self.client.post(self.url, {'quantity': '20'})
        self.assertEqual(response.context['part']['quantity'], 90)
        self.assertEqual(
            Inventory.objects.get(user=self.user, switch__stock=self.switch).quantity,
            90,
        )

    def test_invalid_quantity_rerenders(self):
        response = self.client.post(self.url, {'quantity': '0'})
        self.assertTemplateUsed(response, 'partials/stock_part_collect_modal.html')
        self.assertEqual(response.context['quantity_error'], const.QUANTITY_ERROR)
        self.assertFalse(Inventory.objects.exists())

    def test_bad_params(self):
        url = reverse('stock_part_collect')
        self.assertEqual(self.client.get(f'{url}?type=bogus&id=1').status_code, 400)
        self.assertEqual(self.client.get(f'{url}?type=switch').status_code, 400)
        self.assertEqual(self.client.get(f'{url}?type=switch&id=999').status_code, 404)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code, 302)


class StockPartCatalogViewTests(ClientTestCase):
    def login_with(self, codename):
        user = make_user(codename)
        grant(user, codename)
        self.client.force_login(user)

    def test_permissions_are_separate(self):
        switch = stock_switch()
        params = f'?type=switch&id={switch.pk}'
        for codename, url_name in (
            ('can_upload_stock_data', 'stock_part_edit'),
            ('can_edit_stock_data', 'stock_part_delete'),
            ('can_delete_stock_data', 'stock_part_add'),
        ):
            with self.subTest(url_name=url_name):
                self.login_with(codename)
                url = reverse(url_name) + params
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(StockSwitch.objects.filter(pk=switch.pk).exists())

    def test_add(self):
        self.login_with('can_upload_stock_data')
        url = f'{reverse("stock_part_add")}?type=keycaps'
        self.assertTemplateUsed(self.client.get(url), 'partials/stock_part_modal.html')
        response = self.client.post(
            url, {'keycaps-brand': 'GMK', 'keycaps-name': 'Botanical'}
        )
        self.assertEqual(response['HX-Retarget'], '#table-stock tbody')
        self.assertEqual(str(StockKeycaps.objects.get()), 'GMK Botanical')

    def test_add_invalid_and_bad_type(self):
        self.login_with('can_upload_stock_data')
        response = self.client.post(f'{reverse("stock_part_add")}?type=keycaps', {})
        self.assertTemplateUsed(response, 'partials/stock_part_modal.html')
        self.assertFalse(StockKeycaps.objects.exists())
        self.assertEqual(
            self.client.get(f'{reverse("stock_part_add")}?type=bogus').status_code, 400
        )

    def test_edit_popup_delete_follows_permission(self):
        switch = stock_switch()
        url = f'{reverse("stock_part_edit")}?type=switch&id={switch.pk}'
        delete_url = f'{reverse("stock_part_delete")}?type=switch&amp;ids={switch.pk}'
        self.login_with('can_edit_stock_data')
        self.assertNotContains(self.client.get(url), reverse('stock_part_delete'))
        editor = make_user('editor-deleter')
        grant(editor, 'can_edit_stock_data')
        grant(editor, 'can_delete_stock_data')
        self.client.force_login(editor)
        self.assertContains(self.client.get(url), delete_url)

    def test_edit_keeps_owned_quantity(self):
        self.login_with('can_edit_stock_data')
        switch = stock_switch()
        url = f'{reverse("stock_part_edit")}?type=switch&id={switch.pk}'
        response = self.client.get(url)
        self.assertEqual(response.context['form'].instance, switch)
        response = self.client.post(
            url,
            {
                'switch-brand': 'Gateron',
                'switch-name': 'Milky Yellow',
                'switch-stem': 'mx',
            },
        )
        self.assertEqual(response['HX-Reswap'], 'outerHTML')
        switch.refresh_from_db()
        self.assertEqual(switch.name, 'Milky Yellow')

    def test_delete_keeps_private_copies_for_users(self):
        self.login_with('can_delete_stock_data')
        switch = stock_switch(name='Doomed')
        self.manager.collect_stock_part('switch', switch, 10)
        KeyboardManager(self.other).collect_stock_part('switch', switch, 5)
        build = custom_keyboard(self.user)
        build.switch = Switch.objects.get(stock=switch)
        build.save()
        url = f'{reverse("stock_part_delete")}?type=switch&ids={switch.pk}'

        response = self.client.get(url)
        self.assertEqual(
            response.context['title'], 'Delete Gateron Doomed from the catalog?'
        )
        self.assertEqual(response.context['blocked'], [])

        response = self.client.post(url)
        triggers = json.loads(response['HX-Trigger'])
        self.assertEqual(triggers['rows-deleted']['ids'], [f'stock-switch-{switch.pk}'])
        self.assertFalse(StockSwitch.objects.filter(pk=switch.pk).exists())

        mine = Inventory.objects.get(user=self.user, keyboard__isnull=True)
        theirs = Inventory.objects.get(user=self.other)
        build.refresh_from_db()
        wrappers = [mine.switch, theirs.switch, build.switch]
        self.assertEqual(len({wrapper.pk for wrapper in wrappers}), 3)
        self.assertEqual(len({wrapper.custom_id for wrapper in wrappers}), 3)
        for wrapper in wrappers:
            self.assertIsNone(wrapper.stock_id)
            self.assertEqual(wrapper.custom.name, 'Doomed')
        self.assertEqual((mine.quantity, theirs.quantity), (10, 5))

    def test_delete_blocked_while_prebuilts_use_it(self):
        self.login_with('can_delete_stock_data')
        kit = stock_kit(brand='Wooting', name='60HE')
        prebuilt = stock_keyboard(kit=kit)
        url = f'{reverse("stock_part_delete")}?type=kit&ids={kit.pk}'

        response = self.client.get(url)
        self.assertEqual(
            response.context['blocked'], [('Wooting 60HE', 'Wooting 60HE')]
        )
        self.assertContains(response, 'Nothing can be deleted')
        self.assertNotContains(response, 'type="submit"')

        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(StockKit.objects.filter(pk=kit.pk).exists())
        prebuilt.refresh_from_db()
        self.assertEqual(prebuilt.kit, kit)


class MultiDeleteViewTests(ClientTestCase):
    def assert_rows_deleted(self, response, row_ids):
        triggers = json.loads(response['HX-Trigger'])
        self.assertEqual(sorted(triggers['rows-deleted']['ids']), sorted(row_ids))
        self.assertIn(const.CLOSE_DIALOG_EVENT, triggers)
        self.assertEqual(response['HX-Reswap'], 'none')

    def test_parts(self):
        first, _ = self.manager.collect_stock_part('switch', stock_switch(), 10)
        second, _ = self.manager.collect_stock_part('keycaps', stock_keycaps(), 1)
        theirs, _ = KeyboardManager(self.other).collect_stock_part(
            'switch', stock_switch(name='Red'), 5
        )
        url = reverse('part_delete')
        ids = [first.pk, second.pk, theirs.pk, 'junk']

        response = self.client.get(url, {'ids': ids})
        self.assertTemplateUsed(response, 'partials/delete_modal.html')
        self.assertEqual(response.context['ids'], [first.pk, second.pk])

        response = self.client.post(url, {'ids': ids})
        self.assert_rows_deleted(response, [f'part-{first.pk}', f'part-{second.pk}'])
        self.assertFalse(Inventory.objects.filter(user=self.user).exists())
        self.assertTrue(Inventory.objects.filter(pk=theirs.pk).exists())

    def test_someone_elses_keyboards_ignored(self):
        build = custom_keyboard(self.other)
        response = self.client.post(
            reverse('keyboard_delete'), {'ids': [f'custom-{build.pk}']}
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Inventory.objects.filter(user=self.other).exists())

    def test_stock_prebuilts(self):
        deleter = make_user('deleter')
        grant(deleter, 'can_delete_stock_data')
        owned = prebuilt_in_inventory(self.user)
        other = stock_keyboard()
        url = reverse('stock_prebuilt_delete')
        ids = [owned.pk, other.pk]

        self.assertEqual(self.client.post(url, {'ids': ids}).status_code, 403)
        self.client.force_login(deleter)
        response = self.client.get(url, {'ids': ids})
        self.assertIn('1 user has', response.context['description'])

        response = self.client.post(url, {'ids': ids})
        self.assert_rows_deleted(
            response, [f'prebuilt-{owned.pk}', f'prebuilt-{other.pk}']
        )
        self.assertFalse(StockKeyboard.objects.exists())
        self.assertFalse(Inventory.objects.get(user=self.user).keyboard.obj.stock)

    def test_stock_parts_skip_ones_prebuilts_use(self):
        deleter = make_user('deleter')
        grant(deleter, 'can_delete_stock_data')
        used = stock_switch(name='Used')
        stock_keyboard(switch=used)
        free = stock_switch(name='Free')
        url = f'{reverse("stock_part_delete")}?type=switch'
        ids = [used.pk, free.pk]

        self.assertEqual(self.client.post(url, {'ids': ids}).status_code, 403)
        self.client.force_login(deleter)
        response = self.client.get(f'{url}&ids={used.pk}&ids={free.pk}')
        self.assertEqual(response.context['ids'], [free.pk])
        self.assertEqual(
            [name for name, _ in response.context['blocked']], ['Gateron Used']
        )

        response = self.client.post(url, {'ids': ids})
        self.assert_rows_deleted(response, [f'stock-switch-{free.pk}'])
        self.assertEqual(list(StockSwitch.objects.filter(pk__in=ids)), [used])

    def test_stock_parts_all_blocked(self):
        deleter = make_user('deleter')
        grant(deleter, 'can_delete_stock_data')
        self.client.force_login(deleter)
        used = stock_switch()
        stock_keyboard(switch=used)
        url = f'{reverse("stock_part_delete")}?type=switch'

        response = self.client.get(f'{url}&ids={used.pk}')
        self.assertContains(response, 'Nothing can be deleted')
        self.assertNotContains(response, 'type="submit"')
        self.assertEqual(self.client.post(url, {'ids': [used.pk]}).status_code, 400)
        self.assertTrue(StockSwitch.objects.filter(pk=used.pk).exists())

    def test_nothing_selected(self):
        for name in ('part_delete', 'keyboard_delete'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 400)

    def test_checkboxes_follow_permissions(self):
        stock_switch()
        self.assertNotContains(self.client.get(reverse('stock_switches')), 'data-bulk')
        self.assertContains(
            self.client.get(reverse('inventory_parts')), 'data-bulk-all'
        )
        deleter = make_user('deleter')
        grant(deleter, 'can_delete_stock_data')
        self.client.force_login(deleter)
        response = self.client.get(reverse('stock_switches'))
        self.assertContains(response, 'data-bulk-all')
        self.assertContains(response, 'data-bulk value=')


class PromotePartViewTests(ClientTestCase):
    def setUp(self):
        super().setUp()
        self.uploader = make_user('uploader')
        grant(self.uploader, 'can_upload_stock_data')
        self.client.force_login(self.uploader)
        self.wrapper = custom_kit_wrapper(size='65%', notes='promote me')
        self.inv = Inventory.objects.create(
            user=self.uploader, kit=self.wrapper, quantity=2
        )
        self.url = f'{reverse("part_promote")}?id={self.inv.pk}'

    def test_without_permission_forbidden(self):
        Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertFalse(StockKit.objects.exists())

    def test_edit_popup_button_follows_permission(self):
        edit_url = f'{reverse("part_edit")}?id={self.inv.pk}'
        self.assertContains(self.client.get(edit_url), self.url)
        mine = Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        self.client.force_login(self.user)
        response = self.client.get(f'{reverse("part_edit")}?id={mine.pk}')
        self.assertNotContains(response, reverse('part_promote'))

    def test_get_confirms(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'partials/part_promote_modal.html')
        self.assertContains(response, reverse('stock_kits'))

    def test_post_turns_custom_into_stock(self):
        build = custom_keyboard(self.uploader, kit=self.wrapper)
        custom_id = self.wrapper.custom_id
        response = self.client.post(self.url)
        self.assertEqual(response['HX-Retarget'], f'#part-{self.inv.pk}')
        self.assertTrue(response.context['part']['stock'])

        stock = StockKit.objects.get()
        self.assertEqual(
            (stock.brand, stock.name, stock.size, stock.notes),
            ('KBDfans', 'Tofu65', '65%', 'promote me'),
        )
        self.wrapper.refresh_from_db()
        self.assertEqual((self.wrapper.stock, self.wrapper.custom), (stock, None))
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.quantity, 2)
        build.refresh_from_db()
        self.assertEqual(build.kit.obj, stock)
        self.assertFalse(
            CustomKit.objects.filter(pk=custom_id, stockkit__isnull=True).exists()
        )

    def test_stock_part_and_bad_params(self):
        inv, _ = KeyboardManager(self.uploader).collect_stock_part(
            'switch', stock_switch(), 1
        )
        url = reverse('part_promote')
        self.assertEqual(self.client.get(f'{url}?id={inv.pk}').status_code, 400)
        self.assertEqual(self.client.get(f'{url}?id=x').status_code, 400)
        theirs = Inventory.objects.create(user=self.user, kit=custom_kit_wrapper())
        self.assertEqual(self.client.post(f'{url}?id={theirs.pk}').status_code, 404)
        self.assertIsNotNone(Kit.objects.get(pk=theirs.kit_id).custom_id)
