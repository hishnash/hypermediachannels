import pytest
from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer

from hypermediachannels.serializers import HyperChannelsApiModelSerializer
from tests.models import User, UserProfile, Team


class UserSerializer(HyperChannelsApiModelSerializer):
    class Meta:
        model = User
        fields = (
            '@id',
            'username'
        )


class UserProfileSerializer(HyperChannelsApiModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            '@id',
            'user'
        )


class UserConsumer(GenericAsyncAPIConsumer):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserProfileConsumer(GenericAsyncAPIConsumer):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
    applications = {
        'users': UserConsumer,
        'profiles': UserProfileConsumer
    }


@pytest.mark.django_db(transaction=True)
def test_default_params():

    user = User.objects.create(
        username='bob'
    )

    team = Team.objects.create(
        name='The Team'
    )

    profile = UserProfile.objects.create(
        user=user,
        team=team
    )

    data = UserProfileSerializer(
        instance=profile,
        context={'scope': {'demultiplexer_cls': MainDemultiplexer}}
    ).data

    assert data == {
        'user': {'payload': {'action': 'retrieve', 'pk': user.pk}, 'stream': 'users'},
        '@id': {
            'stream': 'profiles',
            'payload': {
                'pk': profile.pk,
                'action': 'retrieve'
            }
        }
    }


@pytest.mark.django_db(transaction=True)
def test_override_lookup():
    user = User.objects.create(
        username='bob'
    )

    team = Team.objects.create(
        name='The Team'
    )

    profile = UserProfile.objects.create(
        user=user,
        team=team
    )

    class UserProfileSerializer(HyperChannelsApiModelSerializer):
        class Meta:
            model = UserProfile
            fields = (
                '@id',
                'user'
            )

            extra_kwargs = {
                'user': {
                    'kwarg_mappings': {
                        'username': 'username',
                        'profile_pk': 'self.pk',
                        'team_pk': 'self.team.pk'
                    }
                },
            }

    data = UserProfileSerializer(
        instance=profile,
        context={'scope': {'demultiplexer_cls': MainDemultiplexer}}
    ).data

    assert data == {
        '@id': {
            'stream': 'profiles',
            'payload': {
                'pk': profile.pk,
                'action': 'retrieve'
            }
        },
        'user': {
            'stream': 'users',
            'payload': {
                'username': 'bob',
                'profile_pk': profile.pk,
                'team_pk': team.pk,
                'action': 'retrieve'
            }
        },
    }


@pytest.mark.django_db(transaction=True)
def test_many_to_many():

    class UserProfileSerializer(HyperChannelsApiModelSerializer):
        class Meta:
            model = UserProfile
            fields = (
                '@id',
                'friends'
            )

            extra_kwargs = {
                'friends': {
                    'action_name': 'friends_with_profiles',
                    'kwarg_mappings': {
                        'user_pk': 'self.user.pk',
                    }
                },
            }


    user = User.objects.create(
        username='boby'
    )

    team = Team.objects.create(
        name='The Team'
    )

    profile = UserProfile.objects.create(
        user=user,
        team=team
    )

    data = UserProfileSerializer(
        instance=profile,
        context={'scope': {'demultiplexer_cls': MainDemultiplexer}}
    ).data

    assert data == {
        '@id': {
            'stream': 'profiles',
            'payload': {
                'pk': profile.pk,
                'action': 'retrieve'
            }
        },
        'friends': {
            'payload': {
                'action': 'friends_with_profiles',
                'user_pk': user.pk
            },
            'stream': 'profiles'
        }
    }
