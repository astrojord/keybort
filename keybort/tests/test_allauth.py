import re

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from tests.base import make_user

PASSWORD = 'correct-horse-battery'
EMAIL = 'new@example.com'


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
