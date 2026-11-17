import json
import zipfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.organizations.models import Membership, Organization
from apps.projects.models import Project

from . import generator
from .models import ApplicationTemplate


class ApplicationTemplateModelTests(TestCase):
    def template_data(self, **overrides):
        data = {
            'name': 'Django Application',
            'slug': 'test-django-application',
            'version': '1.0.0',
            'description': 'A Django application foundation.',
            'category': ApplicationTemplate.Category.BACKEND,
            'icon': 'python',
            'technology_stack': {
                'language': 'Python',
                'framework': 'Django',
                'runtime': 'Python 3.14',
            },
            'configuration_schema': {
                'fields': {
                    'port': {'type': 'integer', 'required': True},
                    'debug': {'type': 'boolean', 'required': False},
                }
            },
        }
        data.update(overrides)
        return data

    def test_template_slug_and_version_are_unique(self):
        ApplicationTemplate.objects.create(**self.template_data())

        with self.assertRaises(IntegrityError):
            ApplicationTemplate.objects.create(**self.template_data())

    def test_only_one_active_version_can_exist_for_a_slug(self):
        ApplicationTemplate.objects.create(**self.template_data())

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ApplicationTemplate.objects.create(
                    **self.template_data(
                        version='2.0.0',
                        is_active=True,
                    )
                )

        inactive = ApplicationTemplate.objects.create(
            **self.template_data(version='2.0.0', is_active=False)
        )
        self.assertFalse(inactive.is_active)

    def test_configuration_schema_requires_supported_field_types(self):
        template = ApplicationTemplate(**self.template_data(
            configuration_schema={'fields': {'port': {'type': 'secret'}}}
        ))

        with self.assertRaises(ValidationError):
            template.full_clean()

    def test_sensitive_metadata_is_rejected(self):
        template = ApplicationTemplate(**self.template_data(
            technology_stack={'framework': 'Django', 'api_key': 'never-store-this'}
        ))

        with self.assertRaises(ValidationError):
            template.full_clean()

    def test_secret_like_configuration_field_names_are_rejected(self):
        template = ApplicationTemplate(**self.template_data(
            configuration_schema={
                'fields': {'private-key': {'type': 'string'}}
            }
        ))

        with self.assertRaises(ValidationError):
            template.full_clean()

    def test_choice_configuration_fields_require_valid_choices(self):
        template = ApplicationTemplate(**self.template_data(
            configuration_schema={
                'fields': {'region': {'type': 'choice', 'choices': 'north'}}
            }
        ))

        with self.assertRaises(ValidationError):
            template.full_clean()


class StarterKitGeneratorTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email='starter@example.com',
            password='AtlasCloud-safe-password-42!',
        )
        self.organization = Organization.objects.create(
            name='Starter workspace',
            slug='starter-workspace',
        )
        self.templates = ApplicationTemplate.objects.filter(
            slug__in=(
                'django-application',
                'fastapi-application',
                'nodejs-application',
                'static-website',
                'postgresql-database',
                'redis-cache',
            ),
            version='1.0.0',
        )

    def test_all_seeded_template_versions_generate_valid_archives(self):
        self.assertEqual(self.templates.count(), 6)

        for template in self.templates:
            with self.subTest(template=template.slug):
                project = Project.objects.create(
                    organization=self.organization,
                    created_by=self.user,
                    name='Portal $1 {{PROJECT_SLUG}}',
                    slug=f'portal-{template.slug}',
                    description='Example project description',
                    template=template,
                    configuration={'port': 4321},
                )
                archive = generator.build_project_archive(
                    template=template,
                    project=project,
                    configuration=project.configuration,
                )

                with zipfile.ZipFile(BytesIO(archive)) as bundle:
                    self.assertIsNone(bundle.testzip())
                    self.assertIn('README.md', bundle.namelist())
                    metadata = json.loads(
                        bundle.read('atlascloud-project.json')
                    )
                    self.assertEqual(
                        metadata['template']['version'],
                        template.version,
                    )
                    self.assertEqual(
                        metadata['configuration'],
                        project.configuration,
                    )
                    readme = bundle.read('README.md').decode('utf-8')
                    self.assertIn(project.name, readme)
                    self.assertIn('{{PROJECT_SLUG}}', readme)

    def test_manifest_cannot_write_files_outside_starter_directory(self):
        template = self.templates.get(slug='django-application')
        project = Project.objects.create(
            organization=self.organization,
            created_by=self.user,
            name='Safe project',
            slug='safe-project',
            template=template,
        )

        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            starter = root / template.slug / template.version
            starter.mkdir(parents=True)
            (starter / 'manifest.json').write_text(
                '{"files": ["../outside.txt"]}',
                encoding='utf-8',
            )
            with patch.object(generator, 'STARTER_FILES_ROOT', root):
                with self.assertRaises(ValueError):
                    generator.build_project_archive(
                        template=template,
                        project=project,
                        configuration={},
                    )

    def test_html_template_escapes_project_supplied_content(self):
        template = self.templates.get(slug='static-website')
        project = Project.objects.create(
            organization=self.organization,
            created_by=self.user,
            name='<script>alert(1)</script>',
            slug='escaped-project',
            template=template,
        )
        archive = generator.build_project_archive(
            template=template,
            project=project,
            configuration={},
        )

        with zipfile.ZipFile(BytesIO(archive)) as bundle:
            html = bundle.read('index.html').decode('utf-8')
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)


class TemplateCatalogFlowTests(TestCase):
    password = 'AtlasCloud-safe-password-42!'

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email='developer@example.com',
            password=self.password,
        )
        self.owner = user_model.objects.create_user(
            email='owner@example.com',
            password=self.password,
        )
        self.organization = Organization.objects.create(
            name='Atlas Engineering',
            slug='atlas-engineering',
        )
        Membership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=Membership.Role.OWNER,
        )
        self.django_template = ApplicationTemplate.objects.create(
            name='Django Application',
            slug='test-django-application',
            version='1.0.0',
            description='Python Django application foundation.',
            category=ApplicationTemplate.Category.BACKEND,
            icon='python',
            technology_stack={'language': 'Python', 'framework': 'Django'},
            configuration_schema={'fields': {'port': {'type': 'integer'}}},
        )
        self.node_template = ApplicationTemplate.objects.create(
            name='Node.js Application',
            slug='test-nodejs-application',
            version='1.0.0',
            description='Node.js frontend application.',
            category=ApplicationTemplate.Category.FRONTEND,
            icon='nodejs',
            technology_stack={'language': 'JavaScript', 'runtime': 'Node.js'},
            configuration_schema={'fields': {'port': {'type': 'integer'}}},
        )
        self.inactive_template = ApplicationTemplate.objects.create(
            name='Legacy Application',
            slug='test-legacy-application',
            version='1.0.0',
            description='An inactive template.',
            category=ApplicationTemplate.Category.OTHER,
            is_active=False,
            configuration_schema={'fields': {}},
        )

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse('templates_catalog:list'))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('templates_catalog:list')}",
        )

    def test_authenticated_user_sees_active_templates_only(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('templates_catalog:list'))

        self.assertContains(response, self.django_template.name)
        self.assertContains(response, self.node_template.name)
        self.assertNotContains(response, self.inactive_template.name)

    def test_search_filters_by_name_and_technology_stack(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('templates_catalog:list'),
            {'query': 'node'},
        )
        self.assertContains(response, self.node_template.name)
        self.assertNotContains(response, self.django_template.name)

        response = self.client.get(
            reverse('templates_catalog:list'),
            {'query': 'Python'},
        )
        self.assertContains(response, self.django_template.name)
        self.assertNotContains(response, self.node_template.name)

    def test_category_filter_works(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('templates_catalog:list'),
            {'category': ApplicationTemplate.Category.FRONTEND},
        )

        self.assertContains(response, self.node_template.name)
        self.assertNotContains(response, self.django_template.name)

    def test_active_template_detail_is_available(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                'templates_catalog:detail',
                args=[self.django_template.slug],
            )
        )

        self.assertContains(response, self.django_template.version)
        self.assertContains(response, 'Django')
        self.assertContains(
            response,
            f'{reverse("projects:create_without_organization")}?template={self.django_template.pk}',
        )

    def test_using_template_redirects_to_shared_project_creation(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                'templates_catalog:use',
                args=[self.django_template.slug],
            )
        )

        self.assertRedirects(
            response,
            f'{reverse("projects:create_without_organization")}?template={self.django_template.pk}',
        )

    def test_user_cannot_use_inactive_template(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                'templates_catalog:use',
                args=[self.inactive_template.slug],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_inactive_template_detail_is_not_available(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                'templates_catalog:detail',
                args=[self.inactive_template.slug],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_organization_owner_has_no_catalog_modification_endpoint(self):
        self.client.force_login(self.owner)

        response = self.client.get('/admin/templates_catalog/applicationtemplate/add/')

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response.url)

    def test_platform_superuser_can_access_catalog_admin(self):
        admin = get_user_model().objects.create_superuser(
            email='platform-admin@example.com',
            password=self.password,
        )
        self.client.force_login(admin)

        response = self.client.get(
            '/admin/templates_catalog/applicationtemplate/add/'
        )

        self.assertEqual(response.status_code, 200)
