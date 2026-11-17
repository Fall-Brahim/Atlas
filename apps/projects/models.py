from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Project(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        ARCHIVED = 'ARCHIVED', 'Archived'

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.PROTECT,
        related_name='projects',
    )
    template = models.ForeignKey(
        'templates_catalog.ApplicationTemplate',
        on_delete=models.PROTECT,
        related_name='projects',
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_projects',
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170)
    description = models.TextField(blank=True)
    configuration = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=('organization', 'slug'),
                name='unique_project_slug_per_organization',
            ),
        ]
        indexes = [
            models.Index(fields=('organization', 'status')),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.organization}: {self.name}'
