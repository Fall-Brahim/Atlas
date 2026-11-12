from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.organizations.models import Membership, Organization
from apps.templates_catalog.models import ApplicationTemplate

from .models import Project


class ProjectFlowTests(TestCase):
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
        for user, role in (
            (self.owner, Membership.Role.OWNER),
            (self.admin, Membership.Role.ADMIN),
            (self.member, Membership.Role.MEMBER),
        ):
            Membership.objects.create(
                organization=self.organization,
                user=user,
                role=role,
            )
        self.template = ApplicationTemplate.objects.create(
            name='Django Application',
            slug='atlas-test-django-application',
            version='1.0.0',
            description='Django foundation',
            category=ApplicationTemplate.Category.BACKEND,
            technology_stack={'language': 'Python'},
            configuration_schema={'fields': {'port': {'type': 'integer'}}},
        )

    def project_url(self, name='platform'):
        return reverse(
            'projects:detail',
            args=[self.organization.slug, name],
        )

    def create_project(self, **kwargs):
        values = {
            'organization': self.organization,
            'created_by': self.owner,
            'name': 'Platform',
            'slug': 'platform',
        }
        values.update(kwargs)
        return Project.objects.create(**values)

    def test_owner_can_create_project_and_becomes_creator(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('projects:create', args=[self.organization.slug]),
            {
                'name': 'Developer Portal',
                'description': 'Internal platform',
                'status': Project.Status.ACTIVE,
                'template': self.template.pk,
            },
        )

        project = Project.objects.get(name='Developer Portal')
        self.assertRedirects(response, self.project_url('developer-portal'))
        self.assertEqual(project.organization, self.organization)
        self.assertEqual(project.created_by, self.owner)
        self.assertEqual(project.status, Project.Status.ACTIVE)

    def test_template_query_parameter_prefills_project_configuration(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('projects:create', args=[self.organization.slug]),
            {'template': self.template.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].initial['template'],
            self.template,
        )

    def test_member_can_create_project(self):
        self.client.force_login(self.member)

        response = self.client.post(
            reverse('projects:create', args=[self.organization.slug]),
            {
                'name': 'Member Project',
                'description': '',
                'status': Project.Status.DRAFT,
                'template': self.template.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Project.objects.get(name='Member Project').created_by, self.member)

    def test_anonymous_user_cannot_create_project(self):
        response = self.client.get(
            reverse('projects:create', args=[self.organization.slug]),
        )

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('projects:create', args=[self.organization.slug])}",
        )

    def test_project_creation_requires_an_active_template(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('projects:create', args=[self.organization.slug]),
            {
                'name': 'Template Required',
                'description': '',
                'status': Project.Status.DRAFT,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].has_error('template'))
        self.assertFalse(Project.objects.filter(name='Template Required').exists())

    def test_member_can_view_projects_but_non_member_cannot(self):
        project = self.create_project()
        self.client.force_login(self.member)
        response = self.client.get(self.project_url(project.slug))
        self.assertContains(response, project.name)

        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.project_url(project.slug)).status_code, 404)

    def test_project_from_another_organization_is_not_accessible(self):
        other = Organization.objects.create(name='Other Team', slug='other-team')
        Membership.objects.create(
            organization=other,
            user=self.outsider,
            role=Membership.Role.MEMBER,
        )
        project = Project.objects.create(
            organization=other,
            created_by=self.outsider,
            name='Other Platform',
            slug='platform',
        )
        self.client.force_login(self.member)

        response = self.client.get(
            reverse('projects:detail', args=[self.organization.slug, project.slug]),
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_and_admin_can_edit_but_member_cannot(self):
        project = self.create_project()
        url = reverse(
            'projects:edit',
            args=[self.organization.slug, project.slug],
        )
        for user in (self.owner, self.admin):
            self.client.force_login(user)
            response = self.client.post(
                url,
                {
                    'name': f'Updated by {user.email}',
                    'description': 'Updated',
                    'status': Project.Status.ACTIVE,
                    'template': self.template.pk,
                },
            )
            self.assertEqual(response.status_code, 302)

        self.client.force_login(self.member)
        self.assertEqual(
            self.client.post(
                url,
                {
                    'name': 'Unauthorized',
                    'description': '',
                    'status': Project.Status.DRAFT,
                    'template': self.template.pk,
                },
            ).status_code,
            404,
        )

    def test_member_cannot_change_project_organization(self):
        project = self.create_project()
        other = Organization.objects.create(name='Other Team', slug='other-team')
        url = reverse('projects:edit', args=[self.organization.slug, project.slug])
        self.client.force_login(self.owner)

        response = self.client.post(
            url,
            {
                'name': 'Still Platform',
                'description': '',
                'status': Project.Status.DRAFT,
                'template': self.template.pk,
                'organization': other.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.organization, self.organization)

    def test_owner_or_admin_can_archive_and_restore_project(self):
        project = self.create_project()
        archive_url = reverse('projects:archive', args=[self.organization.slug, project.slug])
        restore_url = reverse('projects:restore', args=[self.organization.slug, project.slug])
        self.client.force_login(self.admin)

        response = self.client.post(archive_url)
        self.assertRedirects(response, self.project_url(project.slug))
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.ARCHIVED)

        self.client.post(restore_url)
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.DRAFT)

    def test_member_cannot_archive_project(self):
        project = self.create_project()
        self.client.force_login(self.member)

        response = self.client.post(
            reverse('projects:archive', args=[self.organization.slug, project.slug]),
        )

        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.DRAFT)

    def test_archive_and_restore_require_post(self):
        project = self.create_project()
        self.client.force_login(self.owner)

        self.assertEqual(
            self.client.get(
                reverse('projects:archive', args=[self.organization.slug, project.slug]),
            ).status_code,
            405,
        )

    def test_duplicate_slug_is_rejected(self):
        self.create_project()
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('projects:create', args=[self.organization.slug]),
            {
                'name': 'Platform',
                'description': '',
                'status': Project.Status.DRAFT,
                'template': self.template.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].has_error('name'))
        self.assertEqual(Project.objects.filter(organization=self.organization).count(), 1)

    def test_invalid_status_is_rejected(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('projects:create', args=[self.organization.slug]),
            {
                'name': 'Invalid Project',
                'description': '',
                'status': Project.Status.ARCHIVED,
                'template': self.template.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(name='Invalid Project').exists())

    def test_messages_are_generated_for_lifecycle_actions(self):
        project = self.create_project()
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('projects:archive', args=[self.organization.slug, project.slug]),
        )

        self.assertEqual(
            [str(message) for message in get_messages(response.wsgi_request)],
            ['Project archived successfully.'],
        )
