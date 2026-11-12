from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password


User = get_user_model()
INPUT_CLASSES = (
    'mt-1 block w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2.5 '
    'text-slate-900 outline-none transition placeholder:text-slate-400 '
    'focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/30 '
    'dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 '
    'dark:focus:border-cyan-400 dark:focus:ring-cyan-400/30'
)


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'class': INPUT_CLASSES}),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(
            attrs={'autocomplete': 'current-password', 'class': INPUT_CLASSES}
        ),
    )


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(
            attrs={'autocomplete': 'new-password', 'class': INPUT_CLASSES}
        ),
    )
    password2 = forms.CharField(
        label='Password confirmation',
        strip=False,
        widget=forms.PasswordInput(
            attrs={'autocomplete': 'new-password', 'class': INPUT_CLASSES}
        ),
    )

    class Meta:
        model = User
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update(
            {'autocomplete': 'email', 'class': INPUT_CLASSES}
        )

    def clean_email(self):
        email = self.cleaned_data['email']
        email = User.objects.normalize_email(email)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('The two password fields must match.')
        return password2

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            self.instance.email = self.cleaned_data.get('email', self.instance.email)
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user
