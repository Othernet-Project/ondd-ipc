KU_BAND = 'k'
C_BAND = 'c'
UNIVERSAL = 'u'

C_OFF = 5150  # Frequency offset for C band
NA_KU_OFF = 10750  # Frequency offset for North America Ku
UN_LO_OFF = 9750  # Low band offset
UN_HI_OFF = 10600  # High band offset
UN_HI_SW = 11700  # Transponder frequency at which we switch to high band


def kw2xml(**kwargs):
    """ Convert any keyword parameters to XML

    This function does not guarantee the order of the tags.

    Example::

        >>> kw2xml(foo='bar', bar='baz', baz=1)
        '<foo>bar</foo><bar>baz</bar><baz>1</baz>'

    """
    xml = ''
    for k, v in kwargs.items():
        xml += '<%(key)s>%(val)s</%(key)s>' % dict(key=k, val=v)
    return xml


def xml2dict(xml):
    """
    Convert an simple xml node to a dict

    This function only converts the top level children of the given nod
    """
    d = dict()
    for node in xml:
        d[node.tag] = node.text
    return d


def v2pol(volts):
    if volts == '13':
        return 'v'
    elif volts == '18':
        return 'h'
    return '0'


def freq_conv(freq, lnb_type):
    """ Converts transponder frequency to L-band frequency

    The conversion formula requires the LNB type. The type can be either:
    `KU_BAND` or `'k'` for North America Ku band LNB
    `C_BAND` or `'c'` for C band LNB
    `UNIVERSAL` or `'u'` for Universal LNB.

    Example:

        >>> freq_conv(11471, 'u')
        1721

    """
    if lnb_type == KU_BAND:
        # NA Ku band LNB
        return freq - NA_KU_OFF
    if lnb_type == C_BAND:
        # C band LNB
        return abs(freq - C_OFF)
    # Universal
    if freq > UN_HI_SW:
        return freq - UN_HI_OFF
    return freq - UN_LO_OFF


def needs_tone(freq, lnb_type):
    """ Whether LNB needs a 22KHz tone

    Always returns ``True`` for C band and North America Ku band LNBs.
    """
    if lnb_type in (KU_BAND, C_BAND):
        return False
    return freq > UN_HI_SW
