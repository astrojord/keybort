from functools import cached_property

from ..models import Profile


class UserScoped:
    def __init__(self, user):
        self.user = user

    @cached_property
    def profile(self):
        return Profile.objects.get_or_create(user=self.user)[0]
