import json
import os
import time
from urllib import request

import pytest

from jina import Document, Executor, Flow, helper, requests
from jina.serve.runtimes.gateway.http.models import _to_camel_case
from tests import validate_callback

cur_dir = os.path.dirname(os.path.abspath(__file__))

# check if this can be bypassed
IGNORED_FIELDS = ['embedding', 'scores', 'graphInfo', 'evaluations']


@pytest.fixture
def docs():
    return [Document(id=f'{idx}', text=f'doc{idx}') for idx in range(10)]


def test_no_matches_grpc(mocker, docs):
    def validate_response(resp):
        for doc in resp.data.docs:
            assert len(doc.matches) == 0

    mock_on_done = mocker.Mock()
    with Flow().add() as f:
        f.search(inputs=docs, on_done=mock_on_done)
    validate_callback(mock_on_done, validate_response)


@pytest.fixture
def query_dict():
    return {'top_k': 3, 'mode': 'search', 'data': [{'text': 'query'}]}


class MockExecutor(Executor):
    @requests
    def foo(self, docs, *args, **kwargs):
        for doc in docs:
            doc.tags['tag'] = 'test'


def test_no_matches_rest(query_dict):
    port = helper.random_port()
    with Flow(
        protocol='http',
        port=port,
        including_default_value_fields=True,
    ).add(uses=MockExecutor):
        # temporarily adding sleep
        time.sleep(0.5)
        query = json.dumps(query_dict).encode('utf-8')
        req = request.Request(
            f'http://localhost:{port}/search',
            data=query,
            headers={'content-type': 'application/json'},
        )
        resp = request.urlopen(req).read().decode('utf8')
        doc = json.loads(resp)['data'][0]

    assert len(Document.from_dict(doc).matches) == 0
    assert Document.from_dict(doc).tags['tag'] == 'test'
