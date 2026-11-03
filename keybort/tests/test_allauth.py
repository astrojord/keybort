import json
import re
import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import jwt
import requests
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from tests.base import make_user

PASSWORD = 'correct-horse-battery'
EMAIL = 'new@example.com'
SOCIAL_PROVIDERS = {
    'github': {'APP': {'client_id': 'github-id', 'secret': 'github-secret'}},
    'google': {'APP': {'client_id': 'google-id', 'secret': 'google-secret'}},
}


def confirmation_path(message):
    return re.search(r'https?://[^/]+(/accounts/confirm-email/\S+)', message.body)[1]


class EmailVerificationTests(TestCase):
    def setUp(self):
        cache.clear()

    def sign_up(self, client=None):
        return (client or self.client).post(
            reverse('account_signup'),
            {
                'email': EMAIL,
                'username': 'newuser',
                'password1': PASSWORD,
                'password2': PASSWORD,
            },
        )

    def log_in(self, client=None):
        return (client or self.client).post(
            reverse('account_login'), {'login': 'newuser', 'password': PASSWORD}
        )

    def assertLoggedIn(self, client, expected):
        self.assertEqual('_auth_user_id' in client.session, expected)

    def test_signup_sends_confirmation_without_logging_in(self):
        response = self.sign_up()

        self.assertRedirects(response, reverse('account_email_verification_sent'))
        self.assertEqual(mail.outbox[0].to, [EMAIL])
        self.assertLoggedIn(self.client, False)
        self.assertFalse(EmailAddress.objects.get(email=EMAIL).verified)

    def test_unverified_user_cannot_log_in(self):
        self.sign_up()
        anonymous = Client()

        response = self.log_in(anonymous)

        self.assertRedirects(response, reverse('account_email_verification_sent'))
        self.assertLoggedIn(anonymous, False)

    def test_opening_link_asks_for_confirmation_without_verifying(self):
        self.sign_up()
        path = confirmation_path(mail.outbox[0])

        response = self.client.get(path)

        self.assertTemplateUsed(response, 'account/email_confirm.html')
        self.assertContains(response, f'action="{path}"')
        self.assertFalse(EmailAddress.objects.get(email=EMAIL).verified)
        self.assertLoggedIn(self.client, False)

    def test_confirming_verifies_and_logs_in_signup_session(self):
        self.sign_up()

        response = self.client.post(confirmation_path(mail.outbox[0]))

        self.assertRedirects(response, reverse('index'))
        self.assertTrue(EmailAddress.objects.get(email=EMAIL).verified)
        self.assertLoggedIn(self.client, True)

    def test_confirming_in_other_browser_verifies_without_logging_in(self):
        self.sign_up()
        other = Client()

        response = other.post(confirmation_path(mail.outbox[0]))

        self.assertRedirects(response, reverse('account_login'))
        self.assertTrue(EmailAddress.objects.get(email=EMAIL).verified)
        self.assertLoggedIn(other, False)

    def test_verified_user_can_log_in(self):
        self.sign_up()
        Client().post(confirmation_path(mail.outbox[0]))
        returning = Client()

        response = self.log_in(returning)

        self.assertRedirects(response, reverse('index'))
        self.assertLoggedIn(returning, True)

    def test_invalid_link_shows_expired_page(self):
        response = self.client.get(reverse('account_confirm_email', args=['not-a-key']))

        self.assertTemplateUsed(response, 'account/email_confirm.html')
        self.assertContains(response, 'expired or is invalid')

    def test_existing_unverified_user_is_sent_a_link_at_login(self):
        user = User.objects.create_user(
            username='newuser', email=EMAIL, password=PASSWORD
        )

        response = self.log_in()

        self.assertRedirects(response, reverse('account_email_verification_sent'))
        self.assertEqual(mail.outbox[0].to, [EMAIL])
        self.assertTrue(EmailAddress.objects.filter(user=user, email=EMAIL).exists())


class ManageEmailTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.user.email = EMAIL
        self.user.save()
        EmailAddress.objects.create(
            user=self.user, email=EMAIL, primary=True, verified=True
        )
        self.client.force_login(self.user)

    def test_account_page_links_to_email_management(self):
        response = self.client.get(reverse('account'))

        self.assertContains(response, reverse('account_email'))

    def test_email_page_lists_verification_state(self):
        response = self.client.get(reverse('account_email'))

        self.assertContains(response, EMAIL)
        self.assertContains(response, 'Verified')

    def test_added_address_gets_confirmation_mail(self):
        self.client.post(
            reverse('account_email'),
            {'action_add': '', 'email': 'second@example.com'},
        )

        self.assertEqual(mail.outbox[0].to, ['second@example.com'])
        self.assertFalse(EmailAddress.objects.get(email='second@example.com').verified)


def provider_response(payload):
    response = requests.Response()
    response.status_code = 200
    response.headers['Content-Type'] = 'application/json'
    response._content = json.dumps(payload).encode()
    return response


def github_api(emails, uid=1):
    payloads = {
        'https://github.com/login/oauth/access_token': {'access_token': 'token'},
        'https://api.github.com/user': {
            'id': uid,
            'login': 'githubuser',
            'name': 'GitHub User',
            'email': None,
        },
        'https://api.github.com/user/emails': emails,
    }
    return lambda method, url, **kwargs: provider_response(payloads[url])


def google_api(email, verified=True):
    id_token = jwt.encode(
        {
            'iss': 'https://accounts.google.com',
            'aud': 'google-id',
            'sub': '42',
            'exp': int(time.time()) + 3600,
            'email': email,
            'email_verified': verified,
            'given_name': 'Google User',
        },
        'test-signing-key-long-enough-for-hs256',
        algorithm='HS256',
    )
    payload = {'access_token': 'token', 'id_token': id_token}
    return lambda method, url, **kwargs: provider_response(payload)


def github_email(email, verified=True):
    return {'email': email, 'primary': True, 'verified': verified}


@override_settings(SOCIALACCOUNT_PROVIDERS=SOCIAL_PROVIDERS)
class SocialAccountTests(TestCase):
    def setUp(self):
        cache.clear()

    def begin(self, provider, client=None, query=''):
        return (client or self.client).post(reverse(f'{provider}_login') + query)

    def finish(self, provider, api, client=None, query=''):
        client = client or self.client
        location = self.begin(provider, client, query)['Location']
        state = parse_qs(urlparse(location).query)['state'][0]
        with patch('requests.Session.request', side_effect=api):
            return client.get(
                reverse(f'{provider}_callback'), {'code': 'code', 'state': state}
            )

    def assertLoggedInAs(self, user):
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))

    def assertNotLoggedIn(self):
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_page_offers_configured_providers(self):
        response = self.client.get(reverse('account_login'))

        self.assertContains(response, reverse('google_login'))
        self.assertContains(response, reverse('github_login'))

    def test_login_page_hides_unconfigured_providers(self):
        with override_settings(SOCIALACCOUNT_PROVIDERS={}):
            response = self.client.get(reverse('account_login'))

        self.assertNotContains(response, reverse('google_login'))
        self.assertNotContains(response, reverse('github_login'))

    def test_opening_provider_link_asks_before_redirecting(self):
        response = self.client.get(reverse('github_login'))

        self.assertTemplateUsed(response, 'socialaccount/login.html')
        self.assertContains(response, 'Sign In Via GitHub')

    def test_github_redirect_requests_email_scope(self):
        location = self.begin('github')['Location']

        self.assertTrue(location.startswith('https://github.com/login/oauth/authorize'))
        query = parse_qs(urlparse(location).query)
        self.assertEqual(query['client_id'], ['github-id'])
        self.assertIn('user:email', query['scope'][0])

    def test_google_redirect_requests_email_scope(self):
        location = self.begin('google')['Location']

        self.assertTrue(location.startswith('https://accounts.google.com/'))
        query = parse_qs(urlparse(location).query)
        self.assertEqual(query['client_id'], ['google-id'])
        self.assertIn('email', query['scope'][0].split())

    def test_github_verified_email_signs_up_and_logs_in(self):
        response = self.finish('github', github_api([github_email(EMAIL)]))

        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)
        account = SocialAccount.objects.get(provider='github', uid='1')
        self.assertLoggedInAs(account.user)
        self.assertEqual(account.user.username, 'githubuser')
        self.assertFalse(account.user.has_usable_password())
        self.assertTrue(EmailAddress.objects.get(email=EMAIL).verified)
        self.assertEqual(mail.outbox, [])

    def test_github_unverified_email_requires_confirmation(self):
        response = self.finish('github', github_api([github_email(EMAIL, False)]))

        self.assertRedirects(response, reverse('account_email_verification_sent'))
        self.assertNotLoggedIn()
        self.assertFalse(EmailAddress.objects.get(email=EMAIL).verified)
        self.assertEqual(mail.outbox[0].to, [EMAIL])

    def test_github_without_email_asks_for_one(self):
        response = self.finish('github', github_api([]))

        self.assertRedirects(response, reverse('socialaccount_signup'))
        self.assertNotLoggedIn()
        self.assertFalse(User.objects.exists())

        page = self.client.get(reverse('socialaccount_signup'))
        self.assertContains(page, 'use your GitHub account to sign in to Keybort')
        self.assertContains(page, 'name="email"')
        self.assertNotContains(page, 'name="password1"')

    def test_google_verified_email_signs_up_and_logs_in(self):
        response = self.finish('google', google_api(EMAIL))

        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)
        account = SocialAccount.objects.get(provider='google', uid='42')
        self.assertLoggedInAs(account.user)
        self.assertTrue(EmailAddress.objects.get(email=EMAIL).verified)

    def test_google_unverified_email_requires_confirmation(self):
        response = self.finish('google', google_api(EMAIL, verified=False))

        self.assertRedirects(response, reverse('account_email_verification_sent'))
        self.assertNotLoggedIn()
        self.assertEqual(mail.outbox[0].to, [EMAIL])

    def test_returning_social_user_logs_in_to_same_account(self):
        api = github_api([github_email(EMAIL)])
        self.finish('github', api)
        user = SocialAccount.objects.get().user
        self.client.logout()

        self.finish('github', api)

        self.assertLoggedInAs(user)
        self.assertEqual(User.objects.count(), 1)

    def test_email_of_existing_account_does_not_grant_access(self):
        existing = User.objects.create_user('local', EMAIL, PASSWORD)
        EmailAddress.objects.create(
            user=existing, email=EMAIL, primary=True, verified=True
        )

        response = self.finish('github', github_api([github_email(EMAIL)]))

        self.assertRedirects(response, reverse('account_email_verification_sent'))
        self.assertNotLoggedIn()
        self.assertFalse(SocialAccount.objects.exists())
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(mail.outbox[0].to, [EMAIL])

    def test_tampered_state_shows_error_page(self):
        self.begin('github')

        response = self.client.get(
            reverse('github_callback'), {'code': 'code', 'state': 'forged'}
        )

        self.assertTemplateUsed(response, 'socialaccount/authentication_error.html')
        self.assertContains(response, 'Third-Party Login Failure', status_code=401)
        self.assertNotLoggedIn()

    def test_denying_at_provider_shows_cancelled_page(self):
        location = self.begin('github')['Location']
        state = parse_qs(urlparse(location).query)['state'][0]

        response = self.client.get(
            reverse('github_callback'), {'error': 'access_denied', 'state': state}
        )

        self.assertRedirects(response, reverse('socialaccount_login_cancelled'))
        page = self.client.get(reverse('socialaccount_login_cancelled'))
        self.assertContains(page, 'Login Cancelled')


@override_settings(SOCIALACCOUNT_PROVIDERS=SOCIAL_PROVIDERS)
class ConnectedAccountTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('local', EMAIL, PASSWORD)
        EmailAddress.objects.create(
            user=self.user, email=EMAIL, primary=True, verified=True
        )
        self.client.force_login(self.user)
        self.url = reverse('socialaccount_connections')

    def connect(self, emails):
        location = self.client.post(reverse('github_login') + '?process=connect')[
            'Location'
        ]
        state = parse_qs(urlparse(location).query)['state'][0]
        with patch('requests.Session.request', side_effect=github_api(emails)):
            return self.client.get(
                reverse('github_callback'), {'code': 'code', 'state': state}
            )

    def test_account_page_links_to_connections(self):
        self.assertContains(self.client.get(reverse('account')), self.url)

    def test_connections_page_offers_providers(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'Connected Accounts')
        self.assertContains(response, reverse('google_login'))
        self.assertContains(response, reverse('github_login'))

    def test_connecting_attaches_to_current_user(self):
        response = self.connect([github_email('other@example.com')])

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(SocialAccount.objects.get().user, self.user)
        self.assertEqual(User.objects.count(), 1)

    def test_account_connected_to_other_user_is_not_moved(self):
        other = make_user('other')
        account = SocialAccount.objects.create(user=other, provider='github', uid='1')

        self.connect([github_email('other@example.com')])

        account.refresh_from_db()
        self.assertEqual(account.user, other)

    def test_connected_account_can_be_removed_when_password_exists(self):
        account = SocialAccount.objects.create(
            user=self.user, provider='github', uid='1'
        )

        self.assertContains(self.client.get(self.url), 'GitHub')
        response = self.client.post(self.url, {'account': account.pk})

        self.assertRedirects(response, self.url)
        self.assertFalse(SocialAccount.objects.exists())

    def test_last_login_method_cannot_be_removed(self):
        self.user.set_unusable_password()
        self.user.save()
        self.client.force_login(self.user)
        account = SocialAccount.objects.create(
            user=self.user, provider='github', uid='1'
        )

        response = self.client.post(self.url, {'account': account.pk})

        self.assertContains(response, 'role="alert"')
        self.assertTrue(SocialAccount.objects.filter(pk=account.pk).exists())
