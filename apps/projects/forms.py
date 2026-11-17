import math

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.templates_catalog.models import ApplicationTemplate

from .models import Project


INPUT_CLASSES = (
    'mt-1 block w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2.5 '
    'text-slate-900 outline-none transition placeholder:text-slate-400 '
    'focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/30 '
    'dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 '
    'dark:focus:border-cyan-400 dark:focus:ring-cyan-400/30'
)


def validate_finite_number(value):
    if not math.isfinite(value):
        raise ValidationError('Enter a finite number.', code='invalid')


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('name', 'description', 'template', 'status')
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'Application platform',
                }
            ),
            'description': forms.Textarea(
                attrs={'class': INPUT_CLASSES, 'rows': 4}
            ),
            'template': forms.Select(attrs={'class': INPUT_CLASSES}),
            'status': forms.Select(attrs={'class': INPUT_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        require_template = kwargs.pop('require_template', False)
        super().__init__(*args, **kwargs)
        self.fields['template'].label = 'Application template'
        template_queryset = ApplicationTemplate.objects.filter(is_active=True)
        if self.instance and self.instance.template_id:
            template_queryset = ApplicationTemplate.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.template_id)
            )
        self.fields['template'].queryset = template_queryset
        self.fields['template'].required = require_template or bool(
            self.instance and self.instance.template_id
        )
        self.fields['template'].empty_label = 'Choose a template'
        if self.instance and self.instance.template_id:
            self.initial['template'] = self.instance.template_id
        self.fields['status'].choices = [
            choice for choice in Project.Status.choices
            if choice[0] != Project.Status.ARCHIVED
        ]


class ProjectConfigurationForm(forms.Form):
    def __init__(self, *args, template, initial=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = template
        initial = initial or {}

        schema_fields = template.configuration_schema.get('fields', {})
        for field_name, definition in schema_fields.items():
            field_type = definition['type']
            required = definition.get('required', False)
            label = definition.get(
                'label',
                field_name.replace('_', ' ').capitalize(),
            )
            value = initial.get(field_name, definition.get('default'))
            widget = forms.TextInput(attrs={'class': INPUT_CLASSES})

            if field_type == 'string':
                field = forms.CharField(
                    required=required,
                    initial=value,
                    widget=widget,
                )
            elif field_type == 'integer':
                field = forms.IntegerField(
                    required=required,
                    initial=value,
                    widget=forms.NumberInput(attrs={'class': INPUT_CLASSES}),
                )
            elif field_type == 'number':
                field = forms.FloatField(
                    required=required,
                    initial=value,
                    validators=[validate_finite_number],
                    widget=forms.NumberInput(
                        attrs={'class': INPUT_CLASSES, 'step': 'any'}
                    ),
                )
            elif field_type == 'boolean':
                if isinstance(value, bool):
                    value = str(value).lower()
                field = forms.TypedChoiceField(
                    choices=(
                        ('', 'Select an option'),
                        ('true', 'Yes'),
                        ('false', 'No'),
                    ),
                    coerce=lambda choice: choice == 'true',
                    empty_value=None,
                    required=required,
                    initial=value,
                    widget=forms.Select(attrs={'class': INPUT_CLASSES}),
                )
            elif field_type == 'choice':
                choices = [('', 'Select an option')] + [
                    (choice, choice) for choice in definition['choices']
                ]
                field = forms.ChoiceField(
                    choices=choices,
                    required=required,
                    initial=value,
                    widget=forms.Select(attrs={'class': INPUT_CLASSES}),
                )
            else:
                raise ValueError(f'Unsupported configuration type: {field_type}')

            field.label = label
            field.help_text = definition.get('help_text', '')
            self.fields[f'configuration__{field_name}'] = field

    def clean(self):
        cleaned_data = super().clean()
        configuration = {}
        for field_name in self.template.configuration_schema.get('fields', {}):
            key = f'configuration__{field_name}'
            if key not in cleaned_data:
                continue
            value = cleaned_data[key]
            if value is not None:
                configuration[field_name] = value
        self.configuration = configuration
        return cleaned_data
