#!/usr/bin/env python3
# encoding: utf-8

from elasticsearch import Elasticsearch
from cortexutils.analyzer import Analyzer

# utils
import operator
from functools import reduce

def find(path, obj):
    """
    Traverse an object (list/dict) recursively and return the first element matching the path.
    Note that in case during the walk lists are found, only their first element will
    be traversed.
    On the contrary if the last element of the path is a list, the list will
    be returned.
    """
    def traverse(obj, element):
        if isinstance(obj, dict):
            return operator.getitem(obj, element)
        elif isinstance(obj, list) and len(obj):
            return traverse(obj[0], element)
        else:
            return {}
    try:
        return reduce(traverse, path.split('.'), obj)
    except:
        return {}

class ElasticsearchAnalyzer(Analyzer):

    # Analyzer's constructor
    def __init__(self):
        # Call the constructor of the super class
        Analyzer.__init__(self)
        self.endpoint = self.get_param('config.endpoint', None, 'Elasticsearch endpoint is missing')
        self.index = self.get_param('config.index', None, 'Elasticsearch index is missing')
        # optional
        #self.verify = self.get_param('config.verifyssl', True, None)
        self.client = None
        self.service = self.get_param('config.service', None, 'Service parameter is missing')

    def run(self):
        Analyzer.run(self)

        try:
            self.client = Elasticsearch(self.endpoint)
        except Exception as e:
            self.error("Elasticsearch is not available", e)
            return

        result = {}
        es_result = []
        es_result_ = []

        fields = self.get_param('config.{}'.format(self.service), None, '{} is missing'.format(self.data_type))
        data = self.get_param('data', None, 'Data is missing')
        should = []
        try:
            for field in fields:
                should.append({"term": {field: data}})
            if len(fields) > 1:
                res = self.client.search(index=self.index, body={"query": {"constant_score": {"filter": {"bool":{"should": should}}}}})
            else:
                res = self.client.search(index=self.index, body={"query": should[0]})
        except Exception as e:
            self.unexpectedError(e)
            return
        for doc in res['hits']['hits']:
            es_result.append(find("_id", doc))
            es_result_.append(doc['_source'])
        result['ids'] = list(set(es_result))
        result['results'] = es_result_

        # Return the report
        return self.report(result)

    def summary(self, raw):
        taxonomies = []
        namespace = "ELK"
        predicate = "Match"

        value = "{} match(es)".format(len(raw["results"]))
        level = "info" 

        taxonomies.append(self.build_taxonomy(level, namespace, predicate, value))
        return {"taxonomies": taxonomies}


if __name__ == '__main__':
    ElasticsearchAnalyzer().run()

