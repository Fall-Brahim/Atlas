from django.db import migrations


INITIAL_TEMPLATES = [
    {
        'name': 'Django Application',
        'slug': 'django-application',
        'version': '1.0.0',
        'description': 'A production-ready foundation for Django web applications.',
        'category': 'BACKEND',
        'icon': 'python',
        'technology_stack': {
            'language': 'Python',
            'framework': 'Django',
            'runtime': 'Python 3.14',
        },
        'configuration_schema': {
            'fields': {
                'python_version': {'type': 'string', 'required': True, 'default': '3.14'},
                'port': {'type': 'integer', 'required': True, 'default': 8000},
            }
        },
        'documentation': 'Configure the application runtime and listening port before deployment.',
    },
    {
        'name': 'FastAPI Application',
        'slug': 'fastapi-application',
        'version': '1.0.0',
        'description': 'A lightweight foundation for Python APIs built with FastAPI.',
        'category': 'BACKEND',
        'icon': 'python',
        'technology_stack': {
            'language': 'Python',
            'framework': 'FastAPI',
            'runtime': 'Python 3.14',
        },
        'configuration_schema': {
            'fields': {
                'python_version': {'type': 'string', 'required': True, 'default': '3.14'},
                'port': {'type': 'integer', 'required': True, 'default': 8000},
            }
        },
        'documentation': 'Use this template for HTTP APIs and backend services.',
    },
    {
        'name': 'Node.js Application',
        'slug': 'nodejs-application',
        'version': '1.0.0',
        'description': 'A Node.js foundation for web applications and API services.',
        'category': 'BACKEND',
        'icon': 'nodejs',
        'technology_stack': {
            'language': 'JavaScript',
            'runtime': 'Node.js',
            'package_manager': 'npm',
        },
        'configuration_schema': {
            'fields': {
                'node_version': {'type': 'string', 'required': True, 'default': '22'},
                'port': {'type': 'integer', 'required': True, 'default': 3000},
            }
        },
        'documentation': 'Use this template for Node.js services and server-rendered applications.',
    },
    {
        'name': 'Static Website',
        'slug': 'static-website',
        'version': '1.0.0',
        'description': 'A simple foundation for static HTML, CSS and JavaScript websites.',
        'category': 'FRONTEND',
        'icon': 'web',
        'technology_stack': {
            'language': 'HTML',
            'styling': 'CSS',
            'runtime': 'Static files',
        },
        'configuration_schema': {
            'fields': {
                'port': {'type': 'integer', 'required': True, 'default': 8080},
            }
        },
        'documentation': 'Use this template for frontends that do not require a server runtime.',
    },
    {
        'name': 'PostgreSQL Database',
        'slug': 'postgresql-database',
        'version': '1.0.0',
        'description': 'A PostgreSQL database foundation for application persistence.',
        'category': 'DATABASE',
        'icon': 'database',
        'technology_stack': {
            'engine': 'PostgreSQL',
            'version': '17',
        },
        'configuration_schema': {
            'fields': {
                'storage_gb': {'type': 'integer', 'required': True, 'default': 10},
                'database_version': {'type': 'string', 'required': True, 'default': '17'},
            }
        },
        'documentation': 'Credentials and connection details will be provisioned by a future deployment engine.',
    },
    {
        'name': 'Redis Cache',
        'slug': 'redis-cache',
        'version': '1.0.0',
        'description': 'A Redis cache foundation for low-latency application data.',
        'category': 'CACHE',
        'icon': 'redis',
        'technology_stack': {
            'engine': 'Redis',
            'version': '7',
        },
        'configuration_schema': {
            'fields': {
                'memory_mb': {'type': 'integer', 'required': True, 'default': 256},
                'redis_version': {'type': 'string', 'required': True, 'default': '7'},
            }
        },
        'documentation': 'Use this template for cache and ephemeral data workloads.',
    },
]


def seed_initial_templates(apps, schema_editor):
    template_model = apps.get_model('templates_catalog', 'ApplicationTemplate')
    for template_data in INITIAL_TEMPLATES:
        template_model.objects.get_or_create(
            slug=template_data['slug'],
            version=template_data['version'],
            defaults=template_data,
        )


def remove_initial_templates(apps, schema_editor):
    template_model = apps.get_model('templates_catalog', 'ApplicationTemplate')
    template_model.objects.filter(
        slug__in=[template['slug'] for template in INITIAL_TEMPLATES],
        version='1.0.0',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('templates_catalog', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_initial_templates, remove_initial_templates),
    ]
