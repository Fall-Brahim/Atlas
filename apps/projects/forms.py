from django import forms
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
