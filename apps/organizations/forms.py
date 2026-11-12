from django import forms
from django.contrib.auth import get_user_model

from .models import Membership, Organization


INPUT_CLASSES = (
    'mt-1 block w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2.5 '
    'text-slate-900 outline-none transition placeholder:text-slate-400 '
    'focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/30 '
    'dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 '
    'dark:focus:border-cyan-400 dark:focus:ring-cyan-400/30'
)
User = get_user_model()


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'description': forms.Textarea(
                attrs={'class': INPUT_CLASSES, 'rows': 4}
            ),
        }


class MembershipRoleForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ('role',)
        widgets = {
            'role': forms.Select(attrs={'class': INPUT_CLASSES}),
        }

    def __init__(self, *args, allowed_roles=None, **kwargs):
        super().__init__(*args, **kwargs)
        if allowed_roles is not None:
            self.fields['role'].choices = [
                choice for choice in Membership.Role.choices
                if choice[0] in allowed_roles
            ]


class MembershipAddForm(forms.Form):
    email = forms.EmailField(
        label='User email',
        widget=forms.EmailInput(
            attrs={
                'autocomplete': 'email',
                'class': INPUT_CLASSES,
                'placeholder': 'developer@example.com',
            }
        ),
    )
    role = forms.ChoiceField(
        label='Role',
        choices=(
            (Membership.Role.MEMBER, 'Member'),
            (Membership.Role.ADMIN, 'Admin'),
        ),
        widget=forms.Select(attrs={'class': INPUT_CLASSES}),
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.user = None

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data['email'])
        self.user = User.objects.filter(email__iexact=email).first()
        if self.user is None:
            raise forms.ValidationError(
                'This email address does not belong to an existing account.'
            )
        if Membership.objects.filter(
            organization=self.organization,
            user=self.user,
        ).exists():
            raise forms.ValidationError(
                'This user is already a member of this organization.'
            )
        return email
