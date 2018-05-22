import pytest
from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer

from hypermediachannels.serializers import HyperChannelsApiModelSerializer
from tests.models import User


class UserSerializer(HyperChannelsApiModelSerializer):
    class Meta:
        model = User
        fields = (
            '@id',
            'username'
        )


class UserConsumer(GenericAsyncAPIConsumer):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
    applications = {
        'users': UserConsumer
    }


@pytest.mark.django_db(transaction=True)
def test_default_params():

    user = User.objects.create(
        username='bob'
    )

    with pytest.raises(ValueError, message='HyperlinkedIdentityField must be used on an DCRF view that is nested within a demultiplexer', ):
        UserSerializer(instance=user).data

    data = UserSerializer(
        instance=user,
        context={'scope': {'demultiplexer_cls': MainDemultiplexer}}
    ).data

    assert data == {
        'username': 'bob',
        '@id': {
            'stream': 'users',
            'payload': {
                'pk': user.pk,
                'action': 'retrieve'
            }
        }
    }


@pytest.mark.django_db(transaction=True)
def test_override_lookup():

    user = User.objects.create(
        username='bob'
    )

    class UserSerializer(HyperChannelsApiModelSerializer):
        class Meta:
            model = User
            fields = (
                '@id',
                'username'
            )

            extra_kwargs = {
                '@id': {
                    'action_name': 'find_user',
                    'kwarg_mappings': {
                        'username': 'username'
                    }
                },
            }

    data = UserSerializer(
        instance=user,
        context={'scope': {'demultiplexer_cls': MainDemultiplexer}}
    ).data

    assert data == {
        'username': 'bob',
        '@id': {
            'stream': 'users',
            'payload': {
                'username': 'bob',
                'action': 'find_user'
            }
        }
    }