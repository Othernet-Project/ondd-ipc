import xml.etree.ElementTree as ET

try:
    from unittest import mock
except ImportError:
    import mock

import pytest

from ondd_ipc import ipc as mod


MOD = mod.__name__


class FakeExc(Exception):
    pass


@pytest.fixture
def client():
    return mod.ONDDClient('foo.sock')


@mock.patch(MOD + '.connect')
def test_ping(connect, client):
    """ Can use ping() method to test connection to socket """
    ret = client.ping()
    connect.assert_called_once_with(client.socket_path)
    assert ret is True


@mock.patch(MOD + '.socket')
@mock.patch(MOD + '.connect')
def test_ping_failure(connect, mock_socket, client):
    """ Given socket connection fails, ping returns false """
    mock_socket.error = FakeExc
    mock_socket.timeout = FakeExc
    connect.side_effect = FakeExc
    ret = client.ping()
    assert ret is False


@mock.patch.object(mod.ONDDClient, 'parse')
@mock.patch(MOD + '.send')
def test_query(send, parse, client):
    """ Given payload, sends it to socket and parses response """
    ret = client.query('foo')
    send.assert_called_once_with(client.socket_path, 'foo')
    parse.assert_called_once_with(send.return_value)
    assert ret == parse.return_value


@mock.patch.object(mod.ONDDClient, 'parse')
@mock.patch(MOD + '.send')
def test_query_no_data(send, parse, client):
    """ Given send returns no value, returns None """
    send.return_value = None
    ret = client.query('foo')
    send.assert_called_once_with(client.socket_path, 'foo')
    assert parse.call_count == 0
    assert ret is None
