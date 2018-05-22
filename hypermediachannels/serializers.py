from typing import Iterable, Dict, Any, List

from django.db.models import QuerySet

from rest_framework.serializers import (
    ModelSerializer,
    SerializerMetaclass,
    ListSerializer
)

from hypermediachannels.fields import (
    HyperChannelsApiRelationField,
    HyperChannelsApiMixin
)


class HyperChannelsApiListSerializer(HyperChannelsApiMixin,
                                     ListSerializer):
    @property
    def stream_name(self):
        return getattr(self.child.Meta, 'many_stream_name', super().stream_name)

    @property
    def action_name(self):
        return getattr(self.child.Meta, 'many_action_name', super().action_name)

    @property
    def kwarg_mappings(self):
        return getattr(self.child.Meta, 'many_kwarg_mappings', super().kwarg_mappings)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_representation(self, queryset: QuerySet) -> List[Dict]:
        return [
            # strange but we need to use old style `super` here
            super(HyperChannelsApiListSerializer, self).to_representation(item)
            for item in queryset
        ]


class HyperChannelsApiSerializerMetaclass(SerializerMetaclass):
    def __new__(mcs, name: str, bases: Iterable[type],
                attrs: Dict[str, Any]) -> 'HyperChannelsApiModelSerializer':

        if 'Meta' in attrs and getattr(
                attrs['Meta'],
                'list_serializer_class',
                None
                ) is None:

            attrs['Meta'].list_serializer_class = HyperChannelsApiListSerializer
        return super().__new__(mcs, name, bases, attrs)


class HyperlinkedIdentityField(HyperChannelsApiRelationField):
    """
    A read-only field that represents the identity URL for an object, itself.

    This is in contrast to `HyperlinkedRelatedField` which represents the
    URL of relationships to other objects.
    """

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        kwargs['source'] = '*'
        super().__init__(**kwargs)

    def use_pk_only_optimization(self):
        return False


class HyperChannelsApiModelSerializer(
    ModelSerializer,
        metaclass=HyperChannelsApiSerializerMetaclass):

    url_field_name = '@id'
    serializer_related_field = HyperChannelsApiRelationField
    serializer_url_field = HyperlinkedIdentityField


    def get_default_field_names(self, declared_fields, model_info):
        """
        Return the default list of field names that will be used if the
        `Meta.fields` option is not specified.
        """
        return (
                [self.url_field_name] +
                list(declared_fields.keys()) +
                list(model_info.fields.keys()) +
                list(model_info.forward_relations.keys())
        )

    def build_url_field(self, field_name, model_class):
        """
        Create a field representing the object's own URL.
        """
        field_class = self.serializer_url_field
        field_kwargs = {}

        return field_class, field_kwargs
