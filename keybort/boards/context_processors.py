from django.utils.functional import SimpleLazyObject

from .models import Profile


def _show_carpet(user):
    if not user.is_authenticated:
        return True
    saved = Profile.objects.filter(user=user).values_list('show_carpet', flat=True)
    return saved.first() is not False


def preferences(request):
    return {'show_carpet': SimpleLazyObject(lambda: _show_carpet(request.user))}
