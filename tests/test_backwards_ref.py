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
            'username',
            'profile'
        )

        extra_kwargs = {
            'profile': {
                'kwarg_mappings': {
                    'user_pk': 'self.pk',
                }
            },
        }


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
        username='boby'
    )

    team = Team.objects.create(
        name='The Team'
    )

    profile = UserProfile.objects.create(
        user=user,
        team=team
    )

    data = UserSerializer(
        instance=user,
        context={'scope': {'demultiplexer_cls': MainDemultiplexer}}
    ).data

    assert data == {
        'username': 'boby',
        '@id': {
            'stream': 'users',
            'payload': {
                'pk': user.pk,
                'action': 'retrieve'
            }
        },
        'profile': {
            'payload': {
                'action': 'list',
                'user_pk': user.pk
            },
            'stream': 'profiles'
        }
    }


@pytest.mark.django_db(transaction=True)
def test_many_to_many():

    class UserProfileSerializer(HyperChannelsApiModelSerializer):
        class Meta:
            model = UserProfile
            fields = (
                '@id',
                'friended'
            )

            extra_kwargs = {
                'friended': {
                    'action_name': 'friended_by_profiles',
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
        'friended': {
            'payload': {
                'action': 'friended_by_profiles',
                'user_pk': user.pk
            },
            'stream': 'profiles'
        }
    }