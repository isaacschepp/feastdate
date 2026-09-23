"""Date arithmetic and feast-name parsing for church-year dates.

Dates are carried as Julian Day Numbers ("ordinals"), so the Julian and Gregorian
calendars share one number line and the weekday of any ordinal is ``o % 7``
(0 = Monday ... 6 = Sunday).

Calendar codes used throughout:

``'P'``
    Protestant German (the default): Julian to the end of 1699, the Improved Calendar
    from 1 Mar 1700, with the astronomical Easter of 1724 and 1744.
``'G'``
    Gregorian throughout (Catholic territories, from 1582/83).
``'J'``
    Julian throughout.
"""
import re

__all__ = [
    'julian_easter', 'greg_easter', 'easter', 'easter_of',
    'j2o', 'o2j', 'g2o', 'o2g', 'to_ord', 'cal_of_year',
    'fmt', 'show', 'resolve', 'feast_date', 'FeastError',
    'FE', 'MON', 'DAY', 'SWITCH',
]

# ---------------------------------------------------------------------------------------
# Easter and calendar conversion.


def julian_easter(y):
    """(month, day) of Easter Sunday in the Julian calendar."""
    a = y % 4
    b = y % 7
    c = y % 19
    dd = (19 * c + 15) % 30
    e = (2 * a + 4 * b - dd + 34) % 7
    m = (dd + e + 114) // 31
    day = (dd + e + 114) % 31 + 1
    return (m, day)


def j2o(y, m, dd):
    """Julian calendar date -> Julian Day Number."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return dd + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083


def o2j(j):
    """Julian Day Number -> Julian calendar (year, month, day)."""
    c = j + 32082
    dd = (4 * c + 3) // 1461
    e = c - (1461 * dd) // 4
    m = (5 * e + 2) // 153
    return (dd - 4800 + m // 10, m + 3 - 12 * (m // 10), e - (153 * m + 2) // 5 + 1)


MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def fmt(o):
    """``'30 Mar 1656'``: Julian before 1 Mar 1700, Gregorian from it (no weekday, no label)."""
    y, m, d = o2g(o) if o >= SWITCH else o2j(o)
    return f"{d} {MON[m-1]} {y}"


def greg_easter(y):
    """(month, day) of Easter Sunday in the Gregorian calendar (anonymous Gregorian algorithm)."""
    a = y % 19
    b = y // 100
    c = y % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return (month, day)


def g2o(y, m, dd):
    """Gregorian calendar date -> Julian Day Number."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return dd + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def o2g(j):
    """Julian Day Number -> Gregorian calendar (year, month, day)."""
    a = j + 32044
    b = (4 * a + 3) // 146097
    c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    return (100 * b + d - 4800 + m // 10, m + 3 - 12 * (m // 10), e - (153 * m + 2) // 5 + 1)


def easter(y):
    """Ordinal of Easter Sunday as the Protestant German estates kept it.

    Julian Easter to 1699. From 1700 the Improved Calendar, whose Easter was computed
    astronomically rather than by the Gregorian tables. The two agree in every year of
    the calendar's life except 1724 and 1744: the Protestants kept Easter on 9 Apr 1724
    (Gregorian 16 Apr) and 29 Mar 1744 (Gregorian 5 Apr). Parish registers bear this out;
    a Hessian register dates Maundy Thursday 1724 (``Die Viridium``) to 6 April, three
    days before the Protestant Easter and ten days before the Gregorian one.
    """
    if y == 1724:
        return g2o(1724, 4, 9)
    if y == 1744:
        return g2o(1744, 3, 29)
    if y >= 1700:
        m, d = greg_easter(y)
        return g2o(y, m, d)
    m, d = julian_easter(y)
    return j2o(y, m, d)


#: Movable feasts and named Sundays, in days from Easter Sunday.
FE = {'Septuagesima': -63, 'Sexagesima': -56, 'Estomihi': -49, 'Quinquagesima': -49,
      'Shrove Sunday': -49, 'Invocavit': -42, 'Reminiscere': -35, 'Oculi': -28,
      'Laetare': -21, 'Judica': -14, 'Palm Sunday': -7, 'Easter Tuesday': 2,
      'Easter Monday': 1, 'Quasimodogeniti': 7, 'Misericordias Domini': 14,
      'Misericordias': 14, 'Jubilate': 21, 'Cantate': 28, 'Rogate': 35,
      'Vocem jucunditatis': 35, 'Ascension': 39, 'Exaudi': 42, 'Whit Sunday': 49,
      'Pentecost': 49, 'Whit Monday': 50, 'Whit Tuesday': 51, 'Trinity': 56}

# ---------------------------------------------------------------------------------------
# Calendars.

SWITCH = g2o(1700, 3, 1)    # the first Gregorian day in the Protestant estates


def cal_of_year(y, cal):
    """Which calendar a year's *fixed* dates (Christmas, Epiphany) are mostly reckoned in.

    Under ``'P'`` the year 1700 is split: its January and February (to 18 Feb) were still
    Julian. :func:`to_ord` handles that; this answers for the year as a whole.
    """
    if cal == 'P':
        return 'G' if y >= 1700 else 'J'
    return cal


def to_ord(y, m, d, cal):
    """A fixed date -> ordinal, in the calendar in force on that day.

    Under ``'P'`` that is decided by the day, not the year: Epiphany 1700 is Julian
    6 Jan 1700, because the Improved Calendar began only on 1 Mar 1700.
    """
    if cal == 'P':
        o = j2o(y, m, d)
        return o if o < SWITCH else g2o(y, m, d)
    return g2o(y, m, d) if cal == 'G' else j2o(y, m, d)


def easter_of(y, cal):
    """Ordinal of Easter Sunday in year ``y`` under calendar ``cal`` ('P', 'G' or 'J')."""
    if cal == 'P':
        return easter(y)
    if cal == 'G':
        m, d = greg_easter(y)
        return g2o(y, m, d)
    m, d = julian_easter(y)
    return j2o(y, m, d)


DAY = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def show(o, cal):
    """``'Sun 30 Mar 1656 (Julian)'``: the ordinal in the calendar in force on that day."""
    greg = cal == 'G' or (cal == 'P' and o >= SWITCH)
    y, m, d = o2g(o) if greg else o2j(o)
    return "%s %d %s %d (%s)" % (DAY[o % 7], d, MON[m - 1], y,
                                 'Gregorian' if greg else 'Julian')


# ---------------------------------------------------------------------------------------
# Parsing a feast name. Each entry is (prefixes, days from Easter Sunday). A token matches
# when it STARTS WITH a prefix, so `Reminisc.`, `Reminiscere` and `Reminisc:` all land on
# the same row. Longer, more specific prefixes come first.

EASTER_REL = [
    (('septuag',), -63),
    (('sexag',), -56),
    (('estomihi', 'esto', 'quinq', 'fastnacht'), -49),
    (('invoc',), -42),
    (('reminisc',), -35),
    (('oculi',), -28),
    (('laetare', 'laet', 'lat'), -21),
    (('judica',), -14),
    (('palm',), -7),
    (('viridium', 'coena', 'cena', 'grundonnerstag', 'maundy'), -3),
    (('parasceve', 'karfreitag', 'charfreitag', 'good'), -2),
    (('quasimod', 'quasi', 'quas', 'weisser'), 7),
    (('miseric', 'miser'), 14),
    (('jubil',), 21),
    (('cantat',), 28),
    (('rogat', 'voc'), 35),
    (('ascens', 'himmelfahrt'), 39),
    (('exaudi',), 42),
    (('pentecost', 'pent', 'pfingst', 'whit'), 49),
    (('pasch', 'ostern', 'oster', 'easter'), 0),
]
TRIN = ('trinit', 'trin', 'dreifaltig')
ADV = ('advent', 'adv')
EPIPH = ('epiph',)
FERIA = ('feria', 'fer')
# Weekday words English transcriptions use after a feast name: `Whit Monday`.
WEEKDAY_WORDS = {'monday': 1, 'tuesday': 2, 'montag': 1, 'dienstag': 2}
# Fixed feasts, so the weekday can be asked too. (month, day).
FIXED = [
    (('circumcis', 'neujahr'), (1, 1)),
    (('purif', 'lichtmess'), (2, 2)),
    (('annunc', 'mariae verk'), (3, 25)),
    (('johannis', 'joh bapt'), (6, 24)),
    (('michael',), (9, 29)),
    (('martini',), (11, 11)),
    (('andreae', 'andreas'), (11, 30)),
    (('nativ', 'christtag', 'weihnacht', 'christmas'), (12, 25)),
    (('stephan',), (12, 26)),
]
ROMAN = {'i': 1, 'v': 5, 'x': 10, 'l': 50}


def roman(tok):
    """A lower-case Roman numeral 1..27 -> int, else None."""
    if not re.fullmatch(r'[ivxl]+', tok):
        return None
    total, prev = 0, 0
    for ch in reversed(tok):
        v = ROMAN[ch]
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total if 0 < total <= 27 else None


def tokens(text):
    """Lower-case, fold ae/umlauts/sharp s, split on anything that is not a letter or digit."""
    t = text.lower().replace('æ', 'ae').replace('ä', 'a').replace('ö', 'o').replace('ü', 'u')
    t = t.replace('ß', 'ss')
    return [w for w in re.split(r'[^a-z0-9]+', t) if w]


def split_weekday(tok):
    """German compounds carry the weekday inside the word: `ostermontag` is Easter Monday,
    not Easter Sunday. Split them so the weekday counts: ['oster', 'montag']."""
    for wd in WEEKDAY_WORDS:
        if tok.endswith(wd) and len(tok) > len(wd):
            return [tok[:-len(wd)], wd]
    return [tok]


def starts(tok, prefixes):
    return any(tok.startswith(p) for p in prefixes)


class FeastError(ValueError):
    """The text names no feast, no year, or an impossible one (``Dom. 5. Adv.``)."""


def resolve(text, year=None, cal='P'):
    """``(ordinal, description)`` for a feast name. The year may be inside ``text``.

    Any number from 1500 to 1899 in the text is taken as the year; other numbers, Arabic
    or Roman, are the ordinal (``Dom. 9. Trin.``, ``Dom XXIII post Trin.``, ``Fer. 2.``).
    Raises :class:`FeastError` when nothing can be resolved.
    """
    toks = tokens(text)
    nums, words = [], []
    for w in toks:
        m = re.fullmatch(r'(\d+)(?:st|nd|rd|th|da|ma|tia|ta|to|a|o)?', w)
        if m:
            n = int(m.group(1))
            if 1500 <= n <= 1899:
                if year is not None and year != n:
                    raise FeastError('two years given: %d and %d' % (year, n))
                year = n
            else:
                nums.append(n)
            continue
        r = roman(w)
        if r is not None:
            nums.append(r)
            continue
        words.extend(split_weekday(w))
    if year is None:
        raise FeastError('no year: give one, e.g. "Dom. Palm. 1656"')
    n = nums[0] if nums else None

    def has(prefixes):
        return any(starts(w, prefixes) for w in words)

    is_feria = has(FERIA)

    if has(TRIN):
        base = easter_of(year, cal) + 56
        if n is None or is_feria:
            return base + ((n - 1) if is_feria and n else 0), 'Trinity Sunday' if n is None else 'Trinity feria %d' % n
        return base + 7 * n, '%d. Sunday after Trinity' % n
    if has(ADV):
        if n is None or not 1 <= n <= 4:
            raise FeastError('Advent needs its Sunday, 1 to 4')
        xmas = to_ord(year, 12, 25, cal)
        adv4 = xmas - 1 - ((xmas - 1 - 6) % 7)     # the last Sunday before Christmas Day
        return adv4 - 7 * (4 - n), '%d. Sunday of Advent' % n
    if has(EPIPH):
        epi = to_ord(year, 1, 6, cal)
        if n is None:
            return epi, 'Epiphany'
        first = epi + 1 + ((6 - (epi + 1)) % 7)     # the first Sunday after 6 Jan
        return first + 7 * (n - 1), '%d. Sunday after Epiphany' % n
    for prefixes, off in EASTER_REL:
        hit = next((w for w in words if starts(w, prefixes)), None)
        if hit is None:
            continue
        o = easter_of(year, cal) + off
        extra = 0
        if is_feria and n:
            extra = n - 1                           # feria 2 = Monday, 3 = Tuesday
        else:
            extra = next((WEEKDAY_WORDS[w] for w in words if w in WEEKDAY_WORDS), 0)
        return o + extra, (hit if not extra else '%s + %d day(s)' % (hit, extra))
    joined = ' '.join(words)
    for prefixes, (m, d) in FIXED:
        if any(starts(w, prefixes) for w in words) or any(p in joined for p in prefixes if ' ' in p):
            return to_ord(year, m, d, cal), 'fixed feast %d %s' % (d, MON[m - 1])
    if n is not None and 'post' in words:
        raise FeastError('"post" with no feast named: say which (Trin., Epiph.)')
    raise FeastError('no feast recognised in %r' % text)


def feast_date(text, year=None, cal='P'):
    """``feast_date("Dom. Palm.", 1656)`` -> ``'Sun 30 Mar 1656 (Julian)'``."""
    return show(resolve(text, year, cal)[0], cal)
