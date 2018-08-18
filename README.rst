===================================
Hyper Media Channels Rest Framework
===================================

A Hyper Media style serializer for DjangoChannelsRestFramework_.

.. image:: https://travis-ci.org/hishnash/hypermediachannels.svg?branch=master
    :target: https://travis-ci.org/hishnash/hypermediachannels

API USAGE
=========

This is a collection of serialisers and serialiser fields that creats a
hypermidea style like PK

Setting up your consumers
-------------------------

All of your consumers should be mapped through a `AsyncJsonWebsocketDemultiplexer`.

.. code-block:: python

  from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer
  from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
  from hypermediachannels.serializers import HyperChannelsApiModelSerializer

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
      }

Then when configuring your Channels Application add the ``MainDemultiplexer`` as your main consumer. This way all Websocket connections on that URL will run through the ``Demultiplexer``. See DjangoChannelsRestFramework_ for more deaitls on how to write consumers.


HyperChannelsApiModelSerializer
-------------------------------

This can be used inplace of the DRF ``ModelSerializer``. It will (if you
include ``@id`` in the ``fields`` list) add a self reference to the
model being displayed)

eg ``User`` model Serialiser might respond like this if its fields are
``('@id', 'username', 'profile')``

.. code:: js

   {
      @id: {
        stream: 'user',
        payload: {
          action: 'retrieve',
          pk: 1023
         }
      },
      username: 'bob@example.com',
      profile: {
        stream: 'profile',
        payload: {
          action: 'retrieve',
          pk: 23
        }
      }
   }

This will under the hood use ``HyperlinkedIdentityField`` to create the
``@id`` and ``profile`` fields and they will (by default) return these
``retrieve`` objects.

Why do we do this.
~~~~~~~~~~~~~~~~~~

this means that if we then need to lookup that ``profile`` for this user
we can just send the msg:

.. code:: js

   {
     stream: 'profile',
     payload: {
       action: 'retrieve',
       pk: 23
     }
   }

Down the websocket and we will get that item, the frontend code does not
need to track all of these lockup logic, (consider that some models
might have lookup that is not based on ``pk`` for example).

If you need to define a different set of lookup params. You can use the
``kwarg_mappings``, ``stream_name`` and ``action_name`` kwargs to
override this.

eg:

.. code:: python

   class UserSerializer(HyperChannelsApiModelSerializer):
       class Meta:
           model = get_user_model()
           fields = (
               '@id', 'username', 'profile'
           )

           extra_kwargs = {
               'profile': {
                   'action_name': 'user_profile',
                   'kwarg_mappings': {
                       'user_pk': 'self.pk',
                       'team_pk': 'team.pk'
                   }
               },
           }

the ``kwarg_mappings`` will set the value in the response ``user_pk`` by
extracting the ``pk`` value on from the ``User`` instance.

(pre-appending ``self`` to the ``kwarg_mappings`` value means it will do
the lookup based on the instance parsed to the parent ``Serializer``
rather than the instance for this field. In this case a user profile).

so the above would return:

.. code:: js

   {
      @id: {
        stream: 'user',
        payload: {
          action: 'retrieve',
          pk: 1023
         }
      },
      username: 'bob@example.com',
      profile: {
        stream: 'user_profile',
        payload: {
          action: 'retrieve',
          user_pk: 1023,
          team_pk: 234234
        }
      }
   }

You can use ``.`` to access nested values eg. ``profile.team.name``.

Alternatively you can create fields as you would in DRF.
''''''''''''''''''''''''''''''''''''''''''''''''''''''''

.. code:: python

   class UserSerializer(HyperChannelsApiModelSerializer):
       team = HyperChannelsApiRelationField(
           source='profile.team',
           kwarg_mappings={
               'member_username': 'self.username'
           }
       )

       class Meta:
           model = get_user_model()
           fields = (
               '@id', 'username', 'team'
           )

this will return:

.. code:: js

   {
      @id: {
        stream: 'user',
        payload: {
          action: 'retrieve',
          pk: 1023
         }
      },
      username: 'bob@example.com',
      team: {
        stream: 'team',
        payload: {
          action: 'retrieve',
          member_username: 'bob@example.com'
        }
      }
   }

If you reference a Many field the ``HyperChannelsApiModelSerializer``
will do some magic so that:

.. code:: python

   class UserSerializer(HyperChannelsApiModelSerializer):
       friends = HyperChannelsApiRelationField(
           source='profile.friends'
       )

       class Meta:
           model = get_user_model()
           fields = (
               '@id', 'username', 'friends'
           )



           extra_kwargs = {
               'friends': {
                   'kwarg_mappings': {
                       'user_pk': 'self.user.pk',
                   }
               },
           }

Adding ``extra_kwargs`` for any ``Many`` field can be important so that
you can controle the lookup params used.

**NOTE** all ``Many`` fields (forwards and backwards) will extract
values from the parent instance regardless of if you use ``self.`` in
the ``kwarg_mappings`` value.)

this will return:

.. code:: js

   {
      @id: {
        stream: 'user',
        payload: {
          action: 'retrieve',
          pk: 1023
         }
      },
      username: 'bob@example.com',
      friends: {
           stream: 'user_profile', payload: {action: 'list', user_pk: 1023}
       }
   }

Remember you can also override the ``@id`` lookup/action and stream if
needed, eg:

.. code:: python

   extra_kwargs = {
       '@id': {
           'action_name': 'subscribe_status',
           'kwarg_mappings': {
               'username': 'username'
           }
       },
   }

Returning Many items.
---------------------

Expect to get:

.. code:: js

   [
       {
        stream: 'user',
        payload: {
          action: 'retrieve',
          pk: 1023
         }
       },
       {
        stream: 'user',
        payload: {
          action: 'retrieve',
          pk: 234
         }
      },
       {
        stream: 'user',
        payload: {
          action: 'retrieve',
          pk: 103223
         }
      },
   ]

Rather than getting a fully expanded value for each instance you will
rather just get a list of ``hyper media paths`` you can use to lookup
the instance you need.

If you need to override the ``stream`` ``action`` or ``lookup`` do this:

.. code:: python

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

           many_action_name = 'subscribe'


.. _DjangoChannelsRestFramework: https://github.com/hishnash/djangochannelsrestframework
