from django.core.exceptions import ValidationError
from django.db import models


ALLOWED_SCHEMA_TYPES = {'string', 'integer', 'boolean', 'number', 'choice'}


def validate_technology_stack(value):
    if not isinstance(value, dict):
        raise ValidationError('Technology stack must be a JSON object.')
    if any(not isinstance(key, str) for key in value):
        raise ValidationError('Technology stack keys must be strings.')
    if any(_is_sensitive_key(key) for key in value):
        raise ValidationError('Technology stack cannot contain secrets or credentials.')
    if any(isinstance(item, (dict, list)) for item in value.values()):
        raise ValidationError('Technology stack values must be simple JSON values.')


def validate_configuration_schema(value):
    if not isinstance(value, dict):
        raise ValidationError('Configuration schema must be a JSON object.')
    fields = value.get('fields')
    if not isinstance(fields, dict):
        raise ValidationError('Configuration schema must contain a fields object.')
    if any(not isinstance(key, str) for key in fields):
        raise ValidationError('Configuration field names must be strings.')
    for field_name, definition in fields.items():
        if not isinstance(field_name, str) or not isinstance(definition, dict):
            raise ValidationError('Each configuration field must have an object definition.')
        if any(not isinstance(key, str) for key in definition):
            raise ValidationError(
                f'Configuration field "{field_name}" keys must be strings.'
            )
        if not isinstance(definition.get('required', False), bool):
            raise ValidationError(
                f'Configuration field "{field_name}" must define required as a boolean.'
            )
        field_type = definition.get('type')
        if not isinstance(field_type, str) or field_type not in ALLOWED_SCHEMA_TYPES:
            raise ValidationError(
                f'Configuration field "{field_name}" has an unsupported type.'
            )
        if field_type == 'choice':
            choices = definition.get('choices')
            if not isinstance(choices, list) or not choices or any(
                not isinstance(choice, str) for choice in choices
            ):
                raise ValidationError(
                    f'Configuration field "{field_name}" must define a list of string choices.'
                )
        if _is_sensitive_key(field_name) or any(
            _is_sensitive_key(key) for key in definition
        ):
            raise ValidationError('Configuration schemas cannot define secrets or credentials.')


def _is_sensitive_key(key):
    normalized_key = ''.join(character for character in key.lower() if character.isalnum())
    return any(
        sensitive_part in normalized_key
        for sensitive_part in (
            'credential',
            'password',
            'secret',
            'token',
            'privatekey',
            'apikey',
            'accesskey',
        )
    )


class ApplicationTemplate(models.Model):
    class Category(models.TextChoices):
        BACKEND = 'BACKEND', 'Backend'
        FRONTEND = 'FRONTEND', 'Frontend'
        FULLSTACK = 'FULLSTACK', 'Full-stack'
        DATABASE = 'DATABASE', 'Database'
        CACHE = 'CACHE', 'Cache'
        OTHER = 'OTHER', 'Other'

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170)
    version = models.CharField(max_length=30)
    description = models.TextField()
    category = models.CharField(max_length=10, choices=Category.choices)
    icon = models.CharField(max_length=50, blank=True)
    technology_stack = models.JSONField(default=dict, validators=[validate_technology_stack])
    configuration_schema = models.JSONField(
        default=dict,
        validators=[validate_configuration_schema],
    )
    documentation = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name', 'version')
        constraints = [
            models.UniqueConstraint(
                fields=('slug', 'version'),
                name='unique_template_slug_version',
            ),
            models.UniqueConstraint(
                fields=('slug',),
                condition=models.Q(is_active=True),
                name='unique_active_template_per_slug',
            ),
        ]
        indexes = [
            models.Index(fields=('category', 'is_active')),
            models.Index(fields=('is_active', 'name')),
        ]

    def clean(self):
        validate_technology_stack(self.technology_stack)
        validate_configuration_schema(self.configuration_schema)

    def __str__(self):
        return f'{self.name} {self.version}'
