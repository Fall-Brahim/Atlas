from django import forms

from .models import ApplicationTemplate


INPUT_CLASSES = (
    'mt-1 block w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2.5 '
    'text-slate-900 outline-none transition placeholder:text-slate-400 '
    'focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/30 '
    'dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 '
    'dark:focus:border-cyan-400 dark:focus:ring-cyan-400/30'
)


class TemplateSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        label='Search templates',
        widget=forms.TextInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Django, Python, database...',
                'autocomplete': 'off',
            }
        ),
    )
    category = forms.ChoiceField(
        required=False,
        label='Category',
        choices=(('', 'All categories'),) + tuple(ApplicationTemplate.Category.choices),
        widget=forms.Select(attrs={'class': INPUT_CLASSES}),
    )
