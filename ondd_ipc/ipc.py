"""
ipc.py: make XML IPC to ondd via its control socket

Copyright 2014-2015, Outernet Inc.
Some rights reserved.

This software is free software licensed under the terms of GPLv3. See COPYING
file that comes with the source code, or http://www.gnu.org/licenses/gpl.txt.
"""

from __future__ import unicode_literals

import os
import json
import socket
import logging
import xml.etree.ElementTree as ET
from contextlib import contextmanager

from bottle import request

from .utils import v2pol, kw2xml, xml2dict

OUT_ENCODING = 'utf8'
IN_ENCODING = 'utf8'

ONDD_BAD_RESPONSE_CODE = '400'
ONDD_SOCKET_TIMEOUT = 20.0


def xml_get_path(path):
    """ Return XML for getting a path

    :param path:    path of the get request
    """
    return '<get uri="%s" />' % path


def xml_put_path(path, subtree=''):
    """ Return XML for putting a path

    :param path:        path
    :param subtree:     XML fragment for the PUT request
    """
    return '<put uri="%s">%s</put>' % (path, subtree)


def get_text(root, xpath, default=''):
    try:
        return root.find(xpath).text
    except AttributeError:
        return default


def prepare_socket(socket_path):
    sock = socket.socket(socket.AF_UNIX)
    sock.settimeout(ONDD_SOCKET_TIMEOUT)
    sock.connect(socket_path)
    return sock


@contextmanager
def connect(socket_path):
    sock = prepare_socket(socket_path)
    try:
        yield sock
    finally:
        # Permanently close this socket
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()


def read(sock, buffsize=2048):
    """
    Read the data from a socket until exhausted or NULL byte

    :param sock:        socket object
    :param buffsize:    size of the buffer in bytes (2048 by default)
    """
    idata = data = sock.recv(buffsize)
    while idata and b'\0' not in idata:
        idata = sock.recv(buffsize)
        data += idata
    if data[-1] == '\0':
        data = data[:-1]
    return data.decode(IN_ENCODING)


def null_terminate(s):
    """
    Ensures the string is NULL-byte-terminated
    """
    if s[-1] == '\0':
        return s
    return s + '\0'


def send(socket_path, payload):
    """
    Connect to UNIX socket at `socket_path`, send the payload
    and return the response.

    According to ONDD API, payload must be terminated by NULL byte. If the
    supplied payload isn't terminated by NULL byte, one will automatically be
    appended to the end.

    :param socket_path: the UNIX socket to connect to
    :param payload:     the XML payload to send down the pipe
    :returns:           response data
    """
    payload = null_terminate(payload).encode(OUT_ENCODING)

    try:
        with connect(socket_path) as sock:
            sock.send(payload)
            data = read(sock)
    except (socket.error, socket.timeout):
        return None
    else:
        return data


def parse_transfer(transfer):
    path = get_text(transfer, 'path') or ''
    block_count = int(get_text(transfer, 'block_count') or 0)
    block_received = int(get_text(transfer, 'block_received') or 0)
    complete = get_text(transfer, 'complete') == 'yes'
    if complete:
        percentage = 100
    else:
        percentage = block_received * 100 / (block_count or 1)
    return dict(path=path,
                filename=os.path.basename(path),
                hash=get_text(transfer, 'hash'),
                block_count=block_count,
                block_received=block_received,
                percentage=percentage,
                complete=complete)


class ONDDClient(object):

    def __init__(self, socket_path):
        self.socket_path = socket_path

    def ping(self):
        """ Check if ondd endpoint is active."""
        try:
            with connect(self.socket_path):
                return True
        except (socket.error, socket.timeout):
            logging.debug('Could not connect to ONDD socket.')
            return False

    @staticmethod
    def parse(data):
        """
        Parse incoming XML into Etree object

        :param data:    XML string
        :returns:       root node object
        """
        try:
            return ET.fromstring(data.encode('utf8'))
        except ET.ParseError:
            return None

    def query(self, payload):
        data = send(self.socket_path, payload)
        if data:
            return self.parse(data)
        else:
            return None

    def get_status(self):
        """ Get ONDD status """
        payload = xml_get_path('/status')
        root = self.query(payload)
        if root is None:
            return {
                'has_lock': False,
                'signal': 0,
                'snr': 0.0,
                'streams': []
            }

        tuner = root.find('tuner')
        streams = root.find('streams')
        return {
            'has_lock': get_text(tuner, 'lock') == 'yes',
            'signal': int(get_text(tuner, 'signal') or 0),
            'snr': float(get_text(tuner, 'snr', '0.0')),
            'streams': [
                {'id': get_text(s, 'ident'),
                 'bitrate': int(get_text(s, 'bitrate') or 0)}
                for s in streams
            ]
        }

    def get_file_list(self):
        """ Get ONDD file download list """
        payload = xml_get_path('/signaling/')
        root = self.query(payload)

        if root is None:
            return []

        streams = root.find('streams')
        if streams is not None:
            out = []
            for s in streams:
                files = s.find('files')
                for f in files:
                    out.append({
                        'path': get_text(f, 'path'),
                        'size': int(get_text(f, 'size') or 0)
                    })
            return out
        else:
            return []

    def get_cache_storage(self):
        """ Get ONDD cache storage status """
        payload = xml_get_path('/cache-storage')
        root = self.query(payload)
        if root is None:
            return {'used': 0, 'free': 0}

        cache = root.find('cache')
        return {'used': int(get_text(cache, 'used') or 0),
                'free': int(get_text(cache, 'free') or 0)}

    def get_transfers(self):
        """ Get information about the file ONDD is currently processing """
        payload = xml_get_path('/transfers')
        root = self.query(payload)

        if root is None:
            return []

        streams = root.find('streams')
        if streams is not None:
            return [parse_transfer(transfer) for stream in streams
                    for transfer in stream.find('transfers')]
        else:
            return []

    def get_settings(self):
        """ Get ONDD tuner settings """
        payload = xml_get_path('/settings')
        root = self.query(payload)
        if root is None:
            return {
                'frequency': 0,
                'delivery': '',
                'modulation': '',
                'polarization': '',
                'tone': False,
                'azimuth': 0
            }

        tuner = root.find('tuner')
        return {
            'frequency': int(get_text(tuner, 'frequency') or 0),
            'delivery': get_text(tuner, 'delivery'),
            'modulation': get_text(tuner, 'modulation'),
            'polarization': v2pol(get_text(tuner, 'voltage')),
            'tone': get_text(tuner, 'tone') == 'yes',
            'azimuth': int(get_text(tuner, 'azimuth') or 0),
        }

    def set_settings(self, frequency, symbolrate, delivery='dvb-s',
                     modulation='qpsk', tone=True, voltage=13, azimuth=0):
        settings = dict(tone='yes' if tone else 'no',
                        frequency=frequency,
                        symbolrate=symbolrate,
                        delivery=delivery,
                        modulation=modulation,
                        voltage=voltage,
                        azimuth=azimuth)
        payload = xml_put_path('/settings', kw2xml(**settings))
        resp = self.query(payload)
        if resp is None:
            logging.error('Bad response while setting ONDD settings.')
            return ONDD_BAD_RESPONSE_CODE
        return resp.get('code')

    def set_output_path(self, path):
        payload = xml_put_path('/output', kw2xml(path=path))
        resp = self.query(payload)
        if resp is None:
            logging.error('Bad response while setting output path.')
            return ONDD_BAD_RESPONSE_CODE
        return resp.get('code')

    def get_output_path(self, path):
        payload = xml_get_path('/output')
        resp = self.query(payload)
        if resp is None:
            logging.error('Bad response while getting output path.')
            return None
        return resp.get('path')

    def get_events(self):
        """Get ONDD events """
        payload = xml_get_path('/events')
        root = self.query(payload)
        if root is None:
            return []

        events = root.find('events')
        if events is not None:
            return [xml2dict(e) for e in events]
        else:
            return []


class sdr100Client(ONDDClient):
    def get_settings(self):
        with open(request.app.config['sdr.settings_file'], 'w') as input_file:
            return json.load(input_file)

    def set_settings(self, settings, **kwargs):
        # Write the raw settings so they may be retrieved easily later
        with open(request.app.config['sdr.settings_file'], 'w') as output_file:
            json.dump(settings, output_file)
        # Create the text used by sdr100 as an argument string
        settings_text = str(
            'DAEMON_ARGS="'
            '-f {frequency} -u {uncertainty} -r {symbol_rate} -s {sample_rate} '
            '-b {rf_filter}'
            '"'
        ).format(**settings)
        if settings['descrambler']:
            settings_text += ' -w'
        # Write the argument string
        with open(request.app.config['sdr.daemon_args_file'], 'w') as out:
            out.write(settings_text)

    def restart_service(self):
        # TODO: make sure this isn't looping endlessly
        request.app.supervisor.exts.tasks.schedule(
            os.system, args=(request.app.config['sdr.restart_command'],),
            delay=5)
