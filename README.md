# haystack-elasticsearch-raw-query
This python class allows you to use elasticsearch raw queries with django-haystack SearchQuerySet. Most of the code comes from www.stamkracht.com/extending-haystacks-elasticsearch-backend/

# Usage

```python
import custom_elasticsearch as es
results = es.ConfigurableSearchQuerySet().models(SomeModel)
query = { "bool": { "should": [ { "match": { "text": "milk" } }, { "match": { "text": "yogurt" } } ] } }
results = results.custom_query(query)
```

# Installation

Just add `custom_elasticsearch.py` to your app's directory and change the `Haystack_Connections` settings in your `settings.py` file as follows where `some_app` is your app's name:

```python
HAYSTACK_CONNECTIONS = {

    # this is a custom elastic search engine to extend haystack's elasticsearch

    'default': {
        'ENGINE': 'some_app.custom_elasticsearch.ConfigurableElasticSearchEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'elastic_index'),
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'some_app'
    }

}
```
