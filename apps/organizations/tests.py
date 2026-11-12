from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from .models import Membership, Organization


class OrganizationFlowTests(TestCase):
    password = 'AtlasCloud-safe-password-42!'

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            email='owner@example.com',
            password=self.password,
        )
        self.admin = user_model.objects.create_user(
            email='admin@example.com',
            password=self.password,
        )
        self.member = user_model.objects.create_user(
            email='member@example.com',
            password=self.password,
        )
        self.outsider = user_model.objects.create_user(
            email='outsider@example.com',
            password=self.password,
        )
        self.organization = Organization.objects.create(
            name='Atlas Engineering',
            slug='atlas-engineering',
        )
        self.owner_membership = Membership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=Membership.Role.OWNER,
        )
        self.admin_membership = Membership.objects.create(
            organization=self.organization,
            user=self.admin,
            role=Membership.Role.ADMIN,
        )
        self.member_membership = Membership.objects.create(
            organization=self.organization,
            user=self.member,
            role=Membership.Role.MEMBER,
        )

    def test_authenticated_user_creates_organization_as_owner(self):
        self.client.force_login(self.outsider)

        response = self.client.post(
            reverse('organizations:create'),
            {'name': 'New Platform Team', 'description': 'Platform work'},
        )

        organization = Organization.objects.get(name='New Platform Team')
        self.assertRedirects(response, reverse('organizations:detail', args=[organization.slug]))
        self.assertTrue(
            Membership.objects.filter(
                organization=organization,
                user=self.outsider,
                role=Membership.Role.OWNER,
            ).exists()
        )

    def test_anonymous_user_cannot_create_organization(self):
        response = self.client.get(reverse('organizations:create'))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('organizations:create')}",
        )

    def test_member_sees_only_accessible_organizations(self):
        other = Organization.objects.create(name='Other Team', slug='other-team')
        Membership.objects.create(
            organization=other,
            user=self.member,
            role=Membership.Role.MEMBER,
        )
        self.client.force_login(self.member)

        response = self.client.get(reverse('organizations:list'))

        self.assertContains(response, self.organization.name)
        self.assertContains(response, other.name)
        self.assertNotContains(response, 'outsider@example.com')

    def test_non_member_cannot_view_organization_or_members(self):
        self.client.force_login(self.outsider)

        detail = self.client.get(
            reverse('organizations:detail', args=[self.organization.slug])
        )

        self.assertEqual(detail.status_code, 404)

    def test_member_cannot_update_settings_or_manage_members(self):
        self.client.force_login(self.member)

        settings_response = self.client.post(
            reverse('organizations:settings', args=[self.organization.slug]),
            {'name': 'Changed', 'description': ''},
        )
        role_response = self.client.post(
            reverse(
                'organizations:role',
                args=[self.organization.slug, self.member_membership.pk],
            ),
            {'role': Membership.Role.ADMIN},
        )

        self.assertEqual(settings_response.status_code, 404)
        self.assertEqual(role_response.status_code, 404)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.name, 'Atlas Engineering')

    def test_owner_can_add_member_and_success_message_is_created(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('organizations:add', args=[self.organization.slug]),
            {'email': self.outsider.email, 'role': Membership.Role.MEMBER},
        )

        self.assertRedirects(
            response,
            reverse('organizations:detail', args=[self.organization.slug]),
        )
        self.assertTrue(
            Membership.objects.filter(
                organization=self.organization,
                user=self.outsider,
                role=Membership.Role.MEMBER,
            ).exists()
        )
        self.assertEqual(
            [str(message) for message in get_messages(response.wsgi_request)],
            ['Member added successfully.'],
        )

    def test_owner_can_add_admin(self):
        self.client.force_login(self.owner)

        self.client.post(
            reverse('organizations:add', args=[self.organization.slug]),
            {'email': self.outsider.email.upper(), 'role': Membership.Role.ADMIN},
        )

        self.assertEqual(
            Membership.objects.get(
                organization=self.organization,
                user=self.outsider,
            ).role,
            Membership.Role.ADMIN,
        )

    def test_admin_can_add_member_or_admin(self):
        self.client.force_login(self.admin)

        for email, role in (
            ('new-member@example.com', Membership.Role.MEMBER),
            ('new-user@example.com', Membership.Role.ADMIN),
        ):
            user = get_user_model().objects.create_user(
                email=email,
                password=self.password,
            )
            response = self.client.post(
                reverse('organizations:add', args=[self.organization.slug]),
                {'email': user.email, 'role': role},
            )
            self.assertRedirects(
                response,
                reverse('organizations:detail', args=[self.organization.slug]),
            )
            self.assertEqual(
                Membership.objects.get(
                    organization=self.organization,
                    user=user,
                ).role,
                role,
            )

    def test_member_and_non_member_cannot_add_members(self):
        for user in (self.member, self.outsider):
            self.client.force_login(user)
            response = self.client.post(
                reverse('organizations:add', args=[self.organization.slug]),
                {'email': self.outsider.email, 'role': Membership.Role.MEMBER},
            )
            self.assertEqual(response.status_code, 404)
            self.client.logout()

    def test_anonymous_user_cannot_add_members(self):
        response = self.client.post(
            reverse('organizations:add', args=[self.organization.slug]),
            {'email': self.outsider.email, 'role': Membership.Role.MEMBER},
        )

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('organizations:add', args=[self.organization.slug])}",
        )

    def test_unknown_email_is_rejected_with_form_error(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('organizations:add', args=[self.organization.slug]),
            {'email': 'unknown@example.com', 'role': Membership.Role.MEMBER},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['add_member_form'].has_error('email'))
        self.assertContains(response, 'does not belong to an existing account')

    def test_duplicate_membership_is_rejected_with_message(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('organizations:add', args=[self.organization.slug]),
            {'email': self.member.email.upper(), 'role': Membership.Role.ADMIN},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['add_member_form'].has_error('email'))
        self.assertContains(response, 'already a member of this organization')

    def test_owner_role_and_invalid_role_are_rejected(self):
        self.client.force_login(self.owner)

        for role in (Membership.Role.OWNER, 'INVALID'):
            response = self.client.post(
                reverse('organizations:add', args=[self.organization.slug]),
                {'email': self.outsider.email, 'role': role},
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(
                Membership.objects.filter(
                    organization=self.organization,
                    user=self.outsider,
                ).exists()
            )

    def test_add_member_requires_post(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('organizations:add', args=[self.organization.slug])
        )

        self.assertEqual(response.status_code, 405)

    @patch(
        'apps.organizations.views.Membership.objects.create',
        side_effect=IntegrityError,
    )
    def test_membership_integrity_conflict_is_handled(self, create_membership):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('organizations:add', args=[self.organization.slug]),
            {'email': self.outsider.email, 'role': Membership.Role.MEMBER},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already a member of this organization')
        create_membership.assert_called_once()

    def test_admin_can_update_settings_and_change_member_role(self):
        self.client.force_login(self.admin)

        settings_response = self.client.post(
            reverse('organizations:settings', args=[self.organization.slug]),
            {'name': 'Atlas Platform', 'description': 'Updated'},
        )
        role_response = self.client.post(
            reverse(
                'organizations:role',
                args=[self.organization.slug, self.member_membership.pk],
            ),
            {'role': Membership.Role.ADMIN},
        )

        self.assertRedirects(
            settings_response,
            reverse('organizations:detail', args=[self.organization.slug]),
        )
        self.assertRedirects(
            role_response,
            reverse('organizations:detail', args=[self.organization.slug]),
        )
        self.assertEqual(
            Membership.objects.get(pk=self.member_membership.pk).role,
            Membership.Role.ADMIN,
        )

    def test_admin_cannot_change_another_admin_or_owner(self):
        other_admin = get_user_model().objects.create_user(
            email='other-admin@example.com',
            password=self.password,
        )
        other_membership = Membership.objects.create(
            organization=self.organization,
            user=other_admin,
            role=Membership.Role.ADMIN,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                'organizations:role',
                args=[self.organization.slug, other_membership.pk],
            ),
            {'role': Membership.Role.MEMBER},
        )

        self.assertRedirects(
            response,
            reverse('organizations:detail', args=[self.organization.slug]),
        )
        self.assertEqual(
            Membership.objects.get(pk=other_membership.pk).role,
            Membership.Role.ADMIN,
        )

    def test_owner_cannot_be_removed_or_leave(self):
        self.client.force_login(self.owner)

        remove_response = self.client.post(
            reverse(
                'organizations:remove',
                args=[self.organization.slug, self.owner_membership.pk],
            )
        )
        leave_response = self.client.post(
            reverse('organizations:leave', args=[self.organization.slug])
        )

        self.assertRedirects(
            remove_response,
            reverse('organizations:detail', args=[self.organization.slug]),
        )
        self.assertRedirects(leave_response, reverse('organizations:list'))
        self.assertTrue(
            Membership.objects.filter(pk=self.owner_membership.pk).exists()
        )

    def test_admin_can_remove_member_but_not_admin(self):
        self.client.force_login(self.admin)

        member_response = self.client.post(
            reverse(
                'organizations:remove',
                args=[self.organization.slug, self.member_membership.pk],
            )
        )
        admin_response = self.client.post(
            reverse(
                'organizations:remove',
                args=[self.organization.slug, self.admin_membership.pk],
            )
        )

        self.assertRedirects(
            member_response,
            reverse('organizations:detail', args=[self.organization.slug]),
        )
        self.assertRedirects(
            admin_response,
            reverse('organizations:detail', args=[self.organization.slug]),
        )
        self.assertFalse(
            Membership.objects.filter(pk=self.member_membership.pk).exists()
        )
        self.assertTrue(
            Membership.objects.filter(pk=self.admin_membership.pk).exists()
        )

    def test_duplicate_membership_and_second_owner_are_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(
                    organization=self.organization,
                    user=self.member,
                    role=Membership.Role.MEMBER,
                )
        second_owner = get_user_model().objects.create_user(
            email='second-owner@example.com',
            password=self.password,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(
                    organization=self.organization,
                    user=second_owner,
                    role=Membership.Role.OWNER,
                )
