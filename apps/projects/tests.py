import json
import zipfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from apps.organizations.models import Membership, Organization
from apps.templates_catalog.models import ApplicationTemplate

from .forms import ProjectConfigurationForm
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
        self.assertEqual(project.template, self.template)

    def test_generic_project_creation_asks_for_an_organization(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('projects:create_without_organization'),
            {'template': self.template.pk},
        )

        self.assertContains(response, 'Choose an organization')
        self.assertContains(response, self.organization.name)
        self.assertContains(
            response,
            f'{reverse("projects:create", args=[self.organization.slug])}?template={self.template.pk}',
        )

    def test_generic_project_creation_validates_organization_context(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('projects:create_without_organization'),
            {
                'organization': self.organization.slug,
                'template': self.template.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['organization'], self.organization)
        self.assertEqual(
            response.context['selected_template_id'],
            str(self.template.pk),
        )

    def test_generic_project_creation_rejects_non_member_organization(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse('projects:create_without_organization'),
            {'organization': self.organization.slug},
        )

        self.assertEqual(response.status_code, 404)

    def test_template_version_reference_must_be_active_and_valid(self):
        self.client.force_login(self.owner)

        invalid_version_response = self.client.get(
            reverse('projects:create', args=[self.organization.slug]),
            {'template': 999999},
        )
        self.assertEqual(invalid_version_response.status_code, 404)

        self.template.is_active = False
        self.template.save(update_fields=('is_active',))
        inactive_response = self.client.get(
            reverse('projects:create', args=[self.organization.slug]),
            {'template': self.template.pk},
        )
        self.assertEqual(inactive_response.status_code, 404)

    def test_unavailable_or_invalid_template_version_cannot_be_submitted(self):
        inactive_template = ApplicationTemplate.objects.create(
            name='Inactive Template',
            slug='inactive-template',
            version='1.0.0',
            description='Unavailable',
            category=ApplicationTemplate.Category.BACKEND,
            is_active=False,
            configuration_schema={'fields': {}},
        )
        self.client.force_login(self.owner)
        create_url = reverse('projects:create', args=[self.organization.slug])
        project_data = {
            'name': 'Rejected Project',
            'description': '',
            'status': Project.Status.DRAFT,
        }

        for template_id in (inactive_template.pk, 999999):
            response = self.client.post(
                create_url,
                {**project_data, 'template': template_id},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].has_error('template'))

        self.assertFalse(Project.objects.filter(name='Rejected Project').exists())

    def test_project_keeps_exact_template_version_and_protects_it(self):
        project = self.create_project(template=self.template)
        self.template.is_active = False
        self.template.save(update_fields=('is_active',))
        next_version = ApplicationTemplate.objects.create(
            name=self.template.name,
            slug=self.template.slug,
            version='2.0.0',
            description='Updated foundation',
            category=self.template.category,
            technology_stack=self.template.technology_stack,
            configuration_schema=self.template.configuration_schema,
        )

        project.refresh_from_db()
        self.assertEqual(project.template_id, self.template.pk)
        self.assertNotEqual(project.template, next_version)
        with self.assertRaises(ProtectedError):
            self.template.delete()

    def test_owner_can_generate_and_download_configured_template_zip(self):
        template = ApplicationTemplate.objects.get(
            slug='django-application',
            version='1.0.0',
        )
        project = self.create_project(template=template)
        template.is_active = False
        template.save(update_fields=('is_active',))
        ApplicationTemplate.objects.create(
            name=template.name,
            slug=template.slug,
            version='2.0.0',
            description='New Django template version',
            category=template.category,
            technology_stack=template.technology_stack,
            configuration_schema={'fields': {}},
        )
        self.client.force_login(self.owner)
        generate_url = reverse(
            'projects:generate',
            args=[self.organization.slug, project.slug],
        )

        form_response = self.client.get(generate_url)
        self.assertContains(form_response, 'Configure starter application')
        self.assertContains(form_response, 'Python version')

        download_response = self.client.post(
            generate_url,
            {
                'configuration__python_version': '3.14',
                'configuration__port': '8081',
            },
        )

        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response['Content-Type'], 'application/zip')
        project.refresh_from_db()
        self.assertEqual(
            project.configuration,
            {'python_version': '3.14', 'port': 8081},
        )
        with zipfile.ZipFile(BytesIO(download_response.content)) as bundle:
            self.assertIsNone(bundle.testzip())
            self.assertIn('manage.py', bundle.namelist())
            metadata = json.loads(bundle.read('atlascloud-project.json'))
            self.assertEqual(
                metadata['template'],
                {
                    'name': template.name,
                    'slug': template.slug,
                    'version': '1.0.0',
                },
            )
            self.assertEqual(metadata['configuration'], project.configuration)

    def test_invalid_configuration_is_not_saved_or_downloaded(self):
        template = ApplicationTemplate.objects.get(
            slug='django-application',
            version='1.0.0',
        )
        project = self.create_project(template=template)
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse(
                'projects:generate',
                args=[self.organization.slug, project.slug],
            ),
            {
                'configuration__python_version': '3.14',
                'configuration__port': 'not-a-port',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].has_error('configuration__port'))
        project.refresh_from_db()
        self.assertEqual(project.configuration, {})

    def test_non_finite_number_configuration_is_rejected(self):
        template = ApplicationTemplate.objects.create(
            name='Numeric Configuration',
            slug='numeric-configuration',
            version='1.0.0',
            description='Numeric field validation',
            category=ApplicationTemplate.Category.OTHER,
            configuration_schema={
                'fields': {
                    'ratio': {'type': 'number', 'required': True},
                }
            },
        )

        form = ProjectConfigurationForm(
            data={'configuration__ratio': 'NaN'},
            template=template,
        )

        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('configuration__ratio'))

    def test_boolean_and_choice_configuration_values_are_typed(self):
        template = ApplicationTemplate.objects.create(
            name='Typed Configuration',
            slug='typed-configuration',
            version='1.0.0',
            description='Typed schema validation',
            category=ApplicationTemplate.Category.OTHER,
            configuration_schema={
                'fields': {
                    'enabled': {'type': 'boolean', 'required': True},
                    'region': {
                        'type': 'choice',
                        'required': True,
                        'choices': ['local', 'cloud'],
                    },
                }
            },
        )

        form = ProjectConfigurationForm(
            data={
                'configuration__enabled': 'false',
                'configuration__region': 'cloud',
            },
            template=template,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.configuration,
            {'enabled': False, 'region': 'cloud'},
        )

    def test_only_project_managers_can_save_generation_configuration(self):
        template = ApplicationTemplate.objects.get(
            slug='django-application',
            version='1.0.0',
        )
        project = self.create_project(template=template)
        self.client.force_login(self.member)

        response = self.client.post(
            reverse(
                'projects:generate',
                args=[self.organization.slug, project.slug],
            ),
            {
                'configuration__python_version': '3.14',
                'configuration__port': '8081',
            },
        )

        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.configuration, {})

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
        self.assertContains(response, 'Selected')

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
