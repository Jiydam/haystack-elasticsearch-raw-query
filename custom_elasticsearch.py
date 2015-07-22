from haystack.fields import SearchField
from haystack.backends.elasticsearch_backend import ElasticsearchSearchBackend, ElasticsearchSearchQuery
from haystack.backends.elasticsearch_backend import ElasticsearchSearchEngine
from haystack.query import SearchQuerySet
from haystack.constants import DEFAULT_ALIAS, DJANGO_CT
from django.conf import settings

class TagsField(SearchField):
    field_type = "nested"
    properties = {
                "tag": {
                    "type": "string",
                    "index": "not_analyzed",
                    "omit_norms": True,
                    "index_options": "docs"
                },
                "points": {
                    "type": "float"
                }
    }


class ConfigurableElasticBackend(ElasticsearchSearchBackend):

    def build_search_kwargs(self, query_string, sort_by=None, start_offset=0, end_offset=None,
                        fields='', highlight=False, facets=None,
                        date_facets=None, query_facets=None,
                        narrow_queries=None, spelling_query=None,
                        within=None, dwithin=None, distance_point=None,
                        models=None, limit_to_registered_models=None,
                        result_class=None,nested=None, custom_query = None):

        out = super(ConfigurableElasticBackend, self).build_search_kwargs(query_string, sort_by, start_offset, end_offset,
                                                               fields, highlight, facets,
                                                               date_facets, query_facets,
                                                               narrow_queries, spelling_query,
                                                               within, dwithin, distance_point,
                                                               models, limit_to_registered_models,
                                                               result_class)

        if nested:
            out['query'] = self.nested_query_factory(nested)

        elif custom_query:
            out['query'] = custom_query

        return out








    def nested_query_factory(self, nested):
        score_script = "(doc['%s.points'].empty ? 0 : doc['%s.points'].value)" % \
                       (nested['nested_query_path'],nested['nested_query_path'])
        query = {"nested": {
                        "path": nested['nested_query_path'],
                        "score_mode": "total",
                        "query": {
                            "function_score": {
                                "query": {
                                    "terms": {
                                        nested['nested_query_field']: nested['nested_query_terms'],
                                        "minimum_match" : 1
                                    }
                                },
                                "script_score": {
                                    "script" : score_script,
                                    "lang": "mvel"
                                },
                                "boost_mode": "replace"
                            }
                        }
                    }
                }
        return query


    def build_schema(self, fields):
        content_field_name = ''
        mapping = {}

        for field_name, field_class in fields.items():
            field_mapping = {
                'boost': field_class.boost,
                'index': 'analyzed',
                'store': 'yes',
                'type': 'string',
            }

            if field_class.document is True:
                content_field_name = field_class.index_fieldname

            if field_class.field_type in ['date', 'datetime']:
                field_mapping['type'] = 'date'
            elif field_class.field_type == 'integer':
                field_mapping['type'] = 'long'
            elif field_class.field_type == 'float':
                field_mapping['type'] = 'float'
            elif field_class.field_type == 'boolean':
                field_mapping['type'] = 'boolean'
            elif field_class.field_type == 'nested':
                field_mapping['type'] = 'nested'
                try:
                    field_mapping['properties'] = field_class.properties
                except AttributeError:
                    pass
            elif field_class.field_type == 'ngram':
                field_mapping['analyzer'] = "ngram_analyzer"
            elif field_class.field_type == 'edge_ngram':
                field_mapping['analyzer'] = "edgengram_analyzer"
            elif field_class.field_type == 'location':
                field_mapping['type'] = 'geo_point'

            if field_class.stored is False:
                field_mapping['store'] = 'no'

            # Do this last to override `text` fields.
            if field_class.indexed is False or hasattr(field_class, 'facet_for'):
                field_mapping['index'] = 'not_analyzed'

            if field_mapping['type'] == 'string' and field_class.indexed:
                field_mapping["term_vector"] = "with_positions_offsets"

                if not hasattr(field_class, 'facet_for') and not field_class.field_type in('ngram', 'edge_ngram'):
                    field_mapping["analyzer"] = "snowball"

            mapping[field_class.index_fieldname] = field_mapping

        return (content_field_name, mapping)


class ConfigurableSearchQuerySet(SearchQuerySet):

    def custom_query(self, custom_query = None):
        """Adds a custom query"""
        clone = self._clone()
        clone.query.add_custom_query(custom_query)
        return clone


    def nested(self, terms=None, path="tags", field="tag"):
        """Adds arguments for nested to the query"""
        clone = self._clone()
        clone.query.add_nested(terms, path, field)
        return clone

class ConfigurableElasticsearchSearchQuery(ElasticsearchSearchQuery):
    def __init__(self, using=DEFAULT_ALIAS):
        out = super(ConfigurableElasticsearchSearchQuery, self).__init__(using)

        self.nested = {}
        self.custom_query = {}

    def add_custom_query(self, custom_query = None):
        """Adds arguments for custom_score to the query"""
        self.custom_query = custom_query



    def add_nested(self, terms=None, path=None, field=None):
        """Adds arguments for nested to the query"""
        self.nested = {
            'nested_query_terms': terms,
            'nested_query_path': path,
            'nested_query_field': field
        }

    def build_params(self, spelling_query=None, **kwargs):
        """
        Add custom_score and/or nested parameters
        """
        search_kwargs = super(ConfigurableElasticsearchSearchQuery, self).build_params(spelling_query, **kwargs)

        if self.nested:
            search_kwargs['nested'] = self.nested
        if self.custom_query:
            search_kwargs['custom_query'] = self.custom_query

        return search_kwargs

    def _clone(self, klass=None, using=None):
        clone = super(ConfigurableElasticsearchSearchQuery, self)._clone(klass, using)

        clone.nested = self.nested
        clone.custom_query = self.custom_query
        return clone


class ConfigurableElasticSearchEngine(ElasticsearchSearchEngine):
    backend = ConfigurableElasticBackend
    query = ConfigurableElasticsearchSearchQuery