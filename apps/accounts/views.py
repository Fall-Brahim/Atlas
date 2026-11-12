from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.organizations.models import Membership

from .forms import LoginForm, RegistrationForm


def home(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return redirect('accounts:login')


class AccountLoginView(LoginView):
    authentication_form = LoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error(
                'email',
                'An account with this email address already exists.',
            )
            return render(request, 'accounts/register.html', {'form': form})
        login(request, user)
        return redirect('accounts:dashboard')

    return render(request, 'accounts/register.html', {'form': form})


@require_POST
@login_required
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def dashboard(request):
    memberships = Membership.objects.filter(
        user=request.user,
    ).select_related('organization')
    return render(
        request,
        'accounts/dashboard.html',
        {'memberships': memberships},
    )
