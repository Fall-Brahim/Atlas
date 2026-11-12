from django.db import migrations


def update_framework_icons(apps, schema_editor):
    template_model = apps.get_model('templates_catalog', 'ApplicationTemplate')
    template_model.objects.filter(slug='django-application').update(icon='Django')
    template_model.objects.filter(slug='fastapi-application').update(icon='FastAPI')


def restore_python_icons(apps, schema_editor):
    template_model = apps.get_model('templates_catalog', 'ApplicationTemplate')
    template_model.objects.filter(
        slug__in=('django-application', 'fastapi-application')
    ).update(icon='python')


class Migration(migrations.Migration):
    dependencies = [
        ('templates_catalog', '0002_seed_initial_templates'),
    ]

    operations = [
        migrations.RunPython(update_framework_icons, restore_python_icons),
    ]
