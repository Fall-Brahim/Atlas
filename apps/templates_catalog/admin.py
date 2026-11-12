from django.contrib import admin

from .models import ApplicationTemplate


@admin.register(ApplicationTemplate)
class ApplicationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'category', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'slug', 'version', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'name',
                    'slug',
                    'version',
                    'category',
                    'icon',
                    'is_active',
                )
            },
        ),
        (
            'Metadata',
            {
                'fields': (
                    'description',
                    'technology_stack',
                    'configuration_schema',
                    'documentation',
                )
            },
        ),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
