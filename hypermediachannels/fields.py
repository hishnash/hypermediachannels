from typing import Tuple, Optional, Dict, Type, List, Any

from channels.routing import get_default_application
from django.db.models import QuerySet, Model, Manager
from django.http import Http404

from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_attribute
from rest_framework.generics import get_object_or_404
from rest_framework.relations import (
    RelatedField, ManyRelatedField,
    MANY_RELATION_KWARGS
)


class HyperChannelsApiMixin:
    kwarg_mappings = {'pk': 'pk'}
    action_name = 'retrieve'
    stream_name = None

    def __init__(self, action_name=None, **kwargs):

        kwarg_mappings = kwargs.pop('kwarg_mappings', None)

        stream_name = kwargs.pop('stream_name', None)

        super().__init__(**kwargs)

        if action_name is not None:
            self.action_name = action_name
        assert self.action_name is not None, 'The `action_name` argument is ' \
                                             'required.'

        if kwarg_mappings is not None:
            self.kwarg_mappings = kwarg_mappings

        if self.kwarg_mappings is None:
            self.kwarg_mappings = {}

        if stream_name is not None:
            self.stream_name = stream_name


    @property
    def api_demultiplexer(self):
        demultiplexer_cls = self.context.get(
            'scope', {}
        ).get('demultiplexer_cls')
        if demultiplexer_cls is None:
            raise ValueError('{} must be used on an DCRF view that is nested '
                             'within a demultiplexer'.format(
                self.__class__.__name__
            ))
        return demultiplexer_cls

    def resolve(self, model: Type[Model]) -> Tuple[
            Optional[str], Optional[GenericAsyncAPIConsumer]]:

        if self.api_demultiplexer is None:
            return None, None

        if self.stream_name is not None:
            consumer = self.api_demultiplexer.applications[
                self.stream_name
            ]
            stream_name = self.stream_name
        else:
            stream_name, consumer = self._get_resolve(model)

        return stream_name, consumer

    def _get_resolve(self, instance: Type[Model]) -> Tuple[
            Optional[str], Optional[Type[GenericAsyncAPIConsumer]]]:

        matches: List[Tuple[int, str, Type[GenericAsyncAPIConsumer]]] = []

        for (stream, consumer) in self.api_demultiplexer.applications.items():

            if consumer.queryset is None:
                continue

            match = self._get_model_distance(instance, consumer.queryset.model)

            if match is not None:
                matches.append(
                    (
                        match, stream, consumer
                    )
                )

        if matches:
            matches.sort(key=lambda x: x[0])
            _, stream, consumer = matches[0]
            return stream, consumer
        return None, None

    def _get_model_distance(self, model_cls: Type[Model], other_model_cls: Type[Model]) -> Optional[int]:
        """
        Return the distance (in the inheritance tree between to models)
        """
        if model_cls == other_model_cls:
            return 0

        if not issubclass(model_cls, other_model_cls):
            return None

        return model_cls.__bases__.index(other_model_cls)

    def to_representation(self, instance: Model) -> Optional[Dict]:
        stream_name, consumer = self.resolve(type(instance))
        if (stream_name, consumer) == (None, None):
            return

        payload = {
            'action': self.action_name
        }

        payload.update(
            self.extract_lookups(instance)
        )

        return {
            'stream': stream_name,
            'payload': payload
        }

    def extract_lookups(self, instance) -> Dict[str, Any]:
        payload = {}
        for (key, lookup) in self.kwarg_mappings.items():
            payload[key] = self.extract_lookup(instance, key, lookup)
        return payload

    def extract_lookup(self, instance, key, lookup) -> Any:
        lookup_path = lookup.split('.')
        if lookup_path[0] == 'self':
            return get_attribute(
                self.parent.instance,
                lookup_path[1:]
            )
        else:
            return get_attribute(
                instance, lookup_path
            )


class HyperChannelsApiManyRelationField(HyperChannelsApiMixin,
                                        ManyRelatedField):

    action_name = 'list'

    def to_representation(self, value: QuerySet) -> Dict:

        stream_name, consumer = self.resolve(value.model)

        instance = self.parent.instance

        payload = {
            'action': self.action_name
        }

        payload.update(
            self.extract_lookups(instance)
        )

        return {
            'stream': stream_name,
            'payload': payload
        }


class HyperChannelsApiRelationField(HyperChannelsApiMixin, RelatedField):

    @classmethod
    def many_init(cls, *args, **kwargs) -> HyperChannelsApiManyRelationField:
        list_kwargs = {'child_relation': cls(*args, **kwargs)}

        for key in kwargs.keys():
            if key in MANY_RELATION_KWARGS or key in (
                    'kwarg_mappings',
                    'action_name',
                    'stream_name'):
                list_kwargs[key] = kwargs[key]

        return HyperChannelsApiManyRelationField(**list_kwargs)

    def to_internal_value(self, data):
        if isinstance(data, int):
            # assume it is a pk
            try:
                return get_object_or_404(self.get_queryset(), pk=data)
            except Http404:
                raise ValidationError("Not found")
        if isinstance(data, dict):
            stream = data.get('stream', None)
            payload = data.get('payload', None)
            if not (isinstance(stream, str) and isinstance(payload, dict)):
                raise ValidationError(
                    detail='Must be of the format {stream: ...,'
                           ' payload: {..}}'
                )
            action = payload.get('action', None)

            if action is None:
                raise ValidationError(
                    detail="must have an action key"
                )

            consumer_cls = self.api_demultiplexer.applications.get(
                stream
            )  # type: Type[GenericAsyncAPIConsumer]

            if consumer_cls is None:
                raise ValidationError(
                    detail=f"stream {stream} not found."
                )

            if action not in consumer_cls.available_actions:
                raise ValidationError(
                    detail=f"action {action} not supported on {stream}."
                )

            consumer = consumer_cls(self.context.get('scope'))

            try:
                return consumer.get_object(**payload)
            except Http404:
                raise ValidationError("Not found")
            except AssertionError:
                raise ValidationError("Incorrect lookup arguments")
        raise ValidationError(
            detail="Must be either a hyper-media reference or a pk value"
        )
