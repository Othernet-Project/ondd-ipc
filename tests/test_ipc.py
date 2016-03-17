import socket
import xml.etree.ElementTree as ET

try:
    from unittest import mock
except ImportError:
    import mock

import pytest

from ondd_ipc import ipc as mod


MOD = mod.__name__


class FauxExc(Exception):
    """
    We use a custom exception where we don't want the tests to be mixed up with
    random real exceptions.
    """
    pass


def test_xml_get_path():
    """ Given path, returns XML get fragment """
    assert mod.xml_get_path('/status') == '<get uri="/status" />'


def test_xml_put_path():
    """ Given path, returns XML put fragment """
    assert mod.xml_put_path('/settings') == '<put uri="/settings"></put>'


def test_xml_put_subtree():
    """ Given path and subtree, returns XML put fragment with subtree """
    assert mod.xml_put_path('/settings', '<foo>bar</foo>') == (
        '<put uri="/settings"><foo>bar</foo></put>')


@pytest.mark.parametrize('xml,xpath,text', [
    ('<root><foo><bar>1</bar></foo></root>', 'foo/bar', '1'),
    ('<root><bar>1</bar><foo><bar>2</bar></foo></root>', 'foo/bar', '2'),
])
def test_get_text(xml, xpath, text):
    """ Given root node and xpath expression, returns the text """
    root = ET.fromstring(xml)
    assert mod.get_text(root, xpath) == text


@mock.patch(MOD + '.socket', spec=socket)
def test_prepare_socket(mock_socket):
    """ Given socket path, returns UNIX socket connected """
    ret = mod.prepare_socket('foo.sock')
    mock_socket.socket.assert_called_once_with(mock_socket.AF_UNIX)
    assert ret == mock_socket.socket.return_value
    ret.connect.assert_called_once_with('foo.sock')


@mock.patch(MOD + '.socket', spec=socket)
def test_prepare_socket_timeout(mock_socket):
    """ Returned socket will have a timeout set on it """
    ret = mod.prepare_socket('foo.sock')
    ret.settimeout.assert_called_once_with(mod.ONDD_SOCKET_TIMEOUT)


@mock.patch(MOD + '.prepare_socket')
def test_connect(prepare_socket):
    """ Given path creates context that disconnects on exit """
    with mod.connect('foo') as s:
        assert s == prepare_socket.return_value
        assert not s.shutdown.called
        assert not s.close.called
    s.shutdown.assert_called_once_with(socket.SHUT_RDWR)
    s.close.assert_called_once_with()


@mock.patch(MOD + '.prepare_socket')
def test_connect_exception(prepare_socket):
    """ Given exception in context, it will still close the connection """
    try:
        with mod.connect('foo') as s:
            raise RuntimeError('boom!')
    except RuntimeError:
        pass
    s.shutdown.assert_called_once_with(socket.SHUT_RDWR)
    s.close.assert_called_once_with()


def test_read():
    """ Given a socket, reads until NULL byte and returns the data """
    mock_socket = mock.Mock()
    mock_socket.recv.side_effect = [b'a', b'b', b'c', b'd\0', b'e', b'f']
    assert mod.read(mock_socket) == 'abcd'
    mock_socket.recv.assert_has_calls([
        mock.call(2048),
        mock.call(2048),
        mock.call(2048),
        mock.call(2048)])


def test_read_empty():
    """ Given a socket, reads until empty block and returns the data """
    mock_socket = mock.Mock()
    mock_socket.recv.side_effect = [b'a', b'b', b'c', b'd', b'', b'e', b'f']
    assert mod.read(mock_socket) == 'abcd'
    assert mock_socket.recv.call_count == 5


def test_read_with_specific_buffer_size():
    """ Given buffer size, it reads the string that many bytes at once """
    mock_socket = mock.Mock()
    mock_socket.recv.side_effect = [b'a', b'b', b'c', b'd\0', b'e', b'f']
    mod.read(mock_socket, 1)
    mock_socket.recv.assert_has_calls([
        mock.call(1),
        mock.call(1),
        mock.call(1),
        mock.call(1)])


@pytest.mark.parametrize('s,ret', [
    ('foo', 'foo\0'),
    ('foo\0', 'foo\0'),
])
def test_null_terminate(s, ret):
    """ Given a string, it adds NULL byte if it's not already there """
    assert mod.null_terminate(s) == ret


@mock.patch(MOD + '.connect')
@mock.patch(MOD + '.read')
def test_send(read, connect):
    """ Given socket path and payload, it sends payload and returns resp """
    socket = connect.return_value.__enter__.return_value
    ret = mod.send('foo.sock', 'bar')
    connect.assert_called_once_with('foo.sock')
    socket.send.assert_called_once_with('bar\0')
    read.assert_called_once_with(socket)
    assert ret == read.return_value


# We need to patch socket here, because `socket.error` is not a proper
# exception and we can't use that as side_effect
@mock.patch(MOD + '.socket')
@mock.patch(MOD + '.connect')
@mock.patch(MOD + '.read')
def test_send_socket_error(read, connect, mock_socket):
    """ Socket error on send will cause it to return None """
    mock_socket.error = FauxExc
    mock_socket.timeout = FauxExc
    socket = connect.return_value.__enter__.return_value
    socket.send.side_effect = FauxExc
    ret = mod.send('foo.sock', 'bar')
    assert ret is None


# We need to patch socket here, because `socket.error` is not a proper
# exception and we can't use that as side_effect
@mock.patch(MOD + '.socket')
@mock.patch(MOD + '.connect')
@mock.patch(MOD + '.read')
def test_send_read_error(read, connect, mock_socket):
    """ Socket error on read will cause it to return None """
    mock_socket.error = FauxExc
    mock_socket.timeout = FauxExc
    read.side_effect = FauxExc
    ret = mod.send('foo.sock', 'bar')
    assert ret is None


@pytest.mark.parametrize('xml,d', [
    ('''
     <transfer>
     <carousel_id>1</carousel_id>
     <path>foo/bar</path>
     <hash>1234</hash>
     <block_count>10</block_count>
     <block_received>2</block_received>
     <complete>no</complete>
     </transfer>
     ''', {
         'path': 'foo/bar',
         'filename': 'bar',
         'hash': '1234',
         'block_count': 10,
         'block_received': 2,
         'percentage': 20,
         'complete': False,
     }),
    ('''<transfer>
     <carousel_id>1</carousel_id>
     <path>bar/baz</path>
     <hash>4321</hash>
     <block_count>20</block_count>
     <block_received>10</block_received>
     <complete>yes</complete>
     </transfer>
     ''', {
         'path': 'bar/baz',
         'filename': 'baz',
         'hash': '4321',
         'block_count': 20,
         'block_received': 10,
         'percentage': 100,
         'complete': True,
     }),
])
def test_parse_transfer(xml, d):
    """ Given parsed XML, returns transfer dict """
    ret = mod.parse_transfer(ET.fromstring(xml))
    print(ret)
    print(d)
    assert ret == d
