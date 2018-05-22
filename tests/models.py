from django.db import models


class User(models.Model):
    """Simple model to test with."""

    username = models.CharField(max_length=255)


class Team(models.Model):
    name = models.CharField(max_length=256, null=False, blank=False)


class UserProfile(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='profile',
        on_delete=models.CASCADE
    )
    team = models.ForeignKey(
        Team, related_name='profiles',
        on_delete=models.CASCADE
    )

    friends = models.ManyToManyField(
        'UserProfile',
        related_name='friended'
    )
