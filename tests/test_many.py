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
        'users': UserConsumer,
        'active_users': UserConsumer
    }


@pytest.mark.django_db(transaction=True)
def test_default_params():

    user = User.objects.create(
        username='bob'
    )

    data = UserSerializer(
        instance=User.objects.all(),
        many=True,
        context={'scope': {'demultiplexer_cls': MainDemultiplexer}}
    ).data

    assert data == [
        {
            'stream': 'users',
            'payload': {
                'pk': user.pk,
                'action': 'retrieve'
            }
        }
    ]


@pytest.mark.django_db(transaction=True)
def test_custom_mapping():

    class UserSerializer(HyperChannelsApiModelSerializer):

        class Meta:
            model = User
            fields = (
                '@id',
                'username'
            )

            many_stream_name = 'active_users'

            many_kwarg_mappings = {
                'username': 'username'
            }

    user = User.objects.create(
        username='bob'
    )

    data = UserSerializer(
        instance=User.objects.all(),
        many=True,
        context={'scope': {'demultiplexer_cls': MainDemultiplexer}}
    ).data

    assert data == [
        {
            'stream': 'active_users',
            'payload': {
                'username': user.username,
                'action': 'retrieve'
            }
        }
    ]