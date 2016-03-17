import pytest

import ondd_ipc.utils as mod


MOD = mod.__name__

d = dict


class FakeNode:
    def __init__(self, tag, text):
        self.tag = tag
        self.text = text


@pytest.mark.parametrize('kw,out', [
    (d(foo='bar'), '<foo>bar</foo>'),
    (d(bar='baz'), '<bar>baz</bar>'),
    (d(foo=''), '<foo></foo>'),
])
def test_kw2xml(kw, out):
    """ Given kwargs, returns XML fragments matching kwarg names and values """
    s = mod.kw2xml(**kw)
    assert s == out


def test_kw2xml_multiple_args():
    """ Given multiple arguments, converts them all into siblings """
    s = mod.kw2xml(foo='bar', bar='baz')
    # We cannot test for the entire XML output because the order in which the
    # argument dictionary does not have a predictable order. Instead, we will
    # test that each fragment is present in the output.
    assert '<foo>bar</foo>' in s
    assert '<bar>baz</bar' in s


def test_kw2xml_fragments():
    """ kw2xml does not sanitize the values """
    s = mod.kw2xml(foo='</foo>')
    assert s == '<foo></foo></foo>'


@pytest.mark.parametrize('kw,out', [
    (d(foo=1), '<foo>1</foo>'),
    (d(foo=True), '<foo>True</foo>'),
    (d(foo=None), '<foo>None</foo>'),
])
def test_kw2xml_numeric(kw, out):
    """ Given any arguments, coerces values to string """
    s = mod.kw2xml(**kw)
    assert s == out


def test_kw2xml_no_args():
    """ Given no args, returns empty string """
    s = mod.kw2xml()
    assert s == ''


def test_xml2dict():
    """ Given ElementTree nodes, returns dict matching node name and text """
    tree = [
        FakeNode(tag='foo', text='bar'),
        FakeNode(tag='bar', text='baz')
    ]
    d = mod.xml2dict(tree)
    assert d['foo'] == 'bar'
    assert d['bar'] == 'baz'


def test_xml2dict_empty():
    """ Given empty node list, returns empty dict """
    tree = []
    d = mod.xml2dict(tree)
    assert d == {}


@pytest.mark.parametrize('volts,pol', [
    ('13', 'v'),
    ('18', 'h'),
    ('15', '0'),
    ('12', '0'),
    ('19', '0'),
])
def test_v2pol(volts, pol):
    """ Given voltage of 13 or 18, returns polarization, 0 for other values """
    assert mod.v2pol(volts) == pol


@pytest.mark.parametrize('freq,lnb,lfreq', [
    # The transponder frequency values (left) are chosen so that we have one
    # value on each side of the Universal LNB high-low switch offset of
    # 11700 MHz. For LNB types other than Universal, being on either side of
    # the offset should not affect the calculation.
    (11500, 'k', 750),
    (11800, 'k', 1050),
    (11500, 'c', 6350),
    (11800, 'c', 6650),
    (11500, 'u', 1750),
    (11800, 'u', 1200),
    # For C-band, we additionally test that the absolute difference is used
    # (e.g., |2000 MHz - 5150 MHz| = |-3150 MHz| = 3150 MHz)
    (2000, 'c', 3150),
])
def test_freq_conv(freq, lnb, lfreq):
    """ Given transponder frequecy and LNB type, returns L-band frequency """
    assert mod.freq_conv(freq, lnb) == lfreq


@pytest.mark.parametrize('freq,lnb,tone', [
    # The transponder frequency values (left) are chosen so that we have one
    # value on each side of the Universal LNB high-low switch offset of
    # 11700 MHz. For LNB types other than Universal, being on either side of
    # the offset should not affect the calculation.
    (11500, 'k', False),
    (11800, 'k', False),
    (11500, 'c', False),
    (11800, 'c', False),
    (11500, 'u', False),
    (11800, 'u', True),
])
def test_needs_token(freq, lnb, tone):
    """ Given transponder frequency and LNB type, returns tone-needed flag """
    assert mod.needs_tone(freq, lnb) == tone
