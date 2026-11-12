from .models import Membership


def accessible_organizations(request):
    if not request.user.is_authenticated:
        return {'accessible_organizations': []}
    return {
        'accessible_organizations': Membership.objects.filter(
            user=request.user,
        ).select_related('organization'),
    }
