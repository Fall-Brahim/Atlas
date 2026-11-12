from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse
from django.test import TestCase
from unittest.mock import patch


class AccountsConfigurationTests(TestCase):
    def test_accounts_application_is_registered(self):
        config = apps.get_app_config('accounts')

        self.assertEqual(config.name, 'apps.accounts')


class UserModelTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_email_is_the_authentication_identifier(self):
        self.assertEqual(self.user_model.USERNAME_FIELD, 'email')
        self.assertNotIn('username', [field.name for field in self.user_model._meta.get_fields()])
        self.assertTrue(self.user_model._meta.get_field('email').unique)

    def test_user_manager_normalizes_email_and_hashes_password(self):
        user = self.user_model.objects.create_user(
            email='Developer@Example.COM',
            password='strong-password-123',
        )

        self.assertEqual(user.email, 'Developer@example.com')
        self.assertTrue(user.check_password('strong-password-123'))
        self.assertNotEqual(user.password, 'strong-password-123')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_superuser_defaults_to_staff_and_superuser(self):
        user = self.user_model.objects.create_superuser(
            email='admin@example.com',
            password='strong-password-123',
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class AuthenticationFlowTests(TestCase):
    registration_password = 'AtlasCloud-safe-password-42!'

    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            email='developer@example.com',
            password=self.registration_password,
        )

    def test_valid_registration_creates_hashed_active_user(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'email': 'new-developer@example.com',
                'password1': self.registration_password,
                'password2': self.registration_password,
            },
        )

        self.assertRedirects(response, reverse('accounts:dashboard'))
        new_user = self.user_model.objects.get(email='new-developer@example.com')
        self.assertTrue(new_user.is_active)
        self.assertTrue(new_user.check_password(self.registration_password))
        self.assertNotEqual(new_user.password, self.registration_password)
        self.assertFalse(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)

    def test_duplicate_email_is_rejected(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'email': self.user.email,
                'password1': self.registration_password,
                'password2': self.registration_password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].has_error('email'))
        self.assertEqual(self.user_model.objects.filter(email=self.user.email).count(), 1)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'email': self.user.email.upper(),
                'password1': self.registration_password,
                'password2': self.registration_password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].has_error('email'))
        self.assertEqual(self.user_model.objects.filter(email__iexact=self.user.email).count(), 1)

    @patch('apps.accounts.views.RegistrationForm.save', side_effect=IntegrityError)
    def test_registration_handles_database_duplicate_race(self, save):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'email': 'new-developer@example.com',
                'password1': self.registration_password,
                'password2': self.registration_password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].has_error('email'))
        save.assert_called_once()

    def test_password_confirmation_mismatch_is_rejected(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'email': 'new-developer@example.com',
                'password1': self.registration_password,
                'password2': 'different-password-42!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].has_error('password2'))
        self.assertFalse(
            self.user_model.objects.filter(email='new-developer@example.com').exists()
        )

    def test_invalid_password_is_rejected_by_django_validators(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'email': 'new-developer@example.com',
                'password1': 'password',
                'password2': 'password',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].has_error('password1'))

    def test_login_accepts_email_credentials(self):
        response = self.client.post(
            reverse('accounts:login'),
            {
                'username': self.user.email,
                'password': self.registration_password,
            },
        )

        self.assertRedirects(response, reverse('accounts:dashboard'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_invalid_login_uses_generic_error(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': self.user.email, 'password': 'wrong-password'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct email address and password.')

    def test_external_next_url_is_not_used(self):
        response = self.client.post(
            f"{reverse('accounts:login')}?next=https://evil.example",
            {'username': self.user.email, 'password': self.registration_password},
        )

        self.assertRedirects(response, reverse('accounts:dashboard'))

    def test_anonymous_user_is_redirected_from_dashboard(self):
        response = self.client.get(reverse('accounts:dashboard'))

        expected_url = f"{reverse('accounts:login')}?next={reverse('accounts:dashboard')}"
        self.assertRedirects(response, expected_url)

    def test_root_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('accounts:login'))

    def test_root_redirects_authenticated_users_to_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('accounts:dashboard'))

    def test_authenticated_user_can_access_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('accounts:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.email)

    def test_logout_requires_post_and_ends_session(self):
        self.client.force_login(self.user)

        get_response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(post_response, reverse('accounts:login'))
        dashboard_response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(dashboard_response.status_code, 302)
