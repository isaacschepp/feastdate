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


def cal_of_year(y, cal, m=None, d=None):
    """Which calendar a fixed date is reckoned in: ``'J'`` or ``'G'``.

    Under ``'P'`` the year 1700 is split: 1 Jan to 18 Feb were still Julian and the
    Improved Calendar began on 1 Mar. Give the month (and day) to be answered for that
    day, so ``cal_of_year(1700, 'P', 1, 6)`` is ``'J'``. With the year alone the answer is
    for the year as a whole, which from 1700 on is ``'G'``.
    """
    if cal != 'P':
        return cal
    if m is None:
        return 'G' if y >= 1700 else 'J'
    return 'G' if (y, m, d or 1) >= (1700, 3, 1) else 'J'


def to_ord(y, m, d, cal):
    """A fixed date -> ordinal, in the calendar in force on that day.

    Under ``'P'`` that is decided by the day, not the year: Epiphany 1700 is Julian
    6 Jan 1700, because the Improved Calendar began only on 1 Mar 1700.

    Raises :class:`FeastError` for a day that does not exist in that calendar, such as
    30 Feb, 29 Feb 1800 in the Gregorian calendar, or under ``'P'`` 19 to 29 Feb 1700,
    the days the Improved Calendar dropped.
    """
    c = cal_of_year(y, cal, m, d)
    o = g2o(y, m, d) if c == 'G' else j2o(y, m, d)
    if (o2g(o) if c == 'G' else o2j(o)) != (y, m, d):
        raise FeastError('%d %s %d does not exist in the %s calendar'
                         % (d, MON[m - 1] if 1 <= m <= 12 else '?', y,
                            'Gregorian' if c == 'G' else 'Julian'))
    if cal == 'P' and c == 'J' and o >= SWITCH:
        raise FeastError('%d %s 1700 does not exist in the Protestant calendar: '
                         '18 Feb 1700 (Julian) was followed by 1 Mar 1700' % (d, MON[m - 1]))
    return o


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
# when it STARTS WITH a prefix, so `Reminisc.`, `Reminisc:` and `Reminiscere` all land on
# the same row. Longer, more specific prefixes come first.
#
# Every word of the text must be accounted for: a feast name, a number the feast uses, a
# weekday that agrees with the answer, or one of the connecting words below. Anything else
# is refused. A parser that skips what it does not understand answers "2. Ostertag" with
# Easter Sunday, a plausible date with nothing to say it is wrong.

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
# Weekday words that only say which day the feast fell on. The answer must agree.
CHECK_WEEKDAY = {'sunday': 6, 'sonntag': 6, 'sonntags': 6, 'dominica': 6, 'dominicam': 6,
                 'dominicae': 6, 'saturday': 5, 'samstag': 5, 'sonnabend': 5, 'friday': 4,
                 'freitag': 4, 'thursday': 3, 'donnerstag': 3, 'wednesday': 2, 'mittwoch': 2}
# Fixed feasts, so the weekday can be asked too. (month, day).
FIXED = [
    (('circumcis', 'neujahr'), (1, 1)),
    (('purif', 'lichtmess'), (2, 2)),
    (('annunc', 'mari verk'), (3, 25)),
    (('johannis', 'joh bapt'), (6, 24)),
    (('michael',), (9, 29)),
    (('martini',), (11, 11)),
    (('andreae', 'andreas'), (11, 30)),
    (('nativ', 'christtag', 'weihnacht', 'christmas'), (12, 25)),
    (('stephan',), (12, 26)),
]
# The German feasts kept over several days, counted as the 1st, 2nd and 3rd day of the
# feast: `2. Ostertag` is Easter Monday. Each maps the stem of the compound to the word
# the feast is recognised by.
DAY_STEMS = {'oster': 'oster', 'pfingst': 'pfingst', 'weihnacht': 'weihnacht',
             'weihnachts': 'weihnacht', 'christ': 'christtag'}
DAY_SUFFIXES = ('feiertag', 'festtag', 'tage', 'tag')
# The feasts `2. Ostertag` counts the days of: Easter, Pentecost, Christmas.
DAY_FEASTS = {('easter', next(k for k, (p, _o) in enumerate(EASTER_REL) if 'oster' in p)),
              ('easter', next(k for k, (p, _o) in enumerate(EASTER_REL) if 'pfingst' in p)),
              ('fixed', next(k for k, (p, _md) in enumerate(FIXED) if 'weihnacht' in p))}
FEAST_DAYS = 3              # the most days any feast was kept; 'letzter' is the third
# Ordinals written out. The register writes `der dritte Ostertag`, `Feria secunda`.
ORD_WORDS = [(r'(?:erst|zweit|dritt|viert)(?:e|er|en|es|em)?', ('erst', 'zweit', 'dritt', 'viert')),
             (r'(?:prim|secund|terti|quart)(?:a|o|ae|am|us|um|i)?', ('prim', 'secund', 'terti', 'quart')),
             (r'(?:first|second|third|fourth)', ('first', 'second', 'third', 'fourth'))]
LAST_RE = r'letzt(?:e|er|en|es|em)?'
# Words that connect a feast name to the rest of the entry and add nothing to the date.
FILLER = {'dom', 'dni', 'die', 'dies', 'festo', 'festum', 'fest', 'festi', 'feast', 'day',
          'in', 'am', 'an', 'den', 'der', 'dem', 'des', 'd', 'the', 'of', 'war', 'als', 'ipso',
          'mariae', 'maria', 'marie', 'christi', 's', 'st', 'sancti', 'sankt', 'heil', 'hl',
          'heiligen', 'mihi', 'geniti', 'et', 'und'}
FILLER_PREFIXES = ('domin', 'jucund', 'bapt')
# Words that belong to a numbered Sunday AFTER a feast: `Dom. 5. p. Epiph.`
POST = {'post', 'p', 'after', 'nach'}
# Latin and English ordinal endings, and the German ones: `2te`, `3ten`, `2t`.
NUM_RE = r'(\d+)(?:st|nd|rd|th|da|ma|tia|ta|to|a|o|ten|ter|tes|tem|te|t|en|er|e)?'
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


def ord_word(tok):
    """`dritte` / `secunda` / `third` -> 3, else None."""
    for pat, stems in ORD_WORDS:
        if re.fullmatch(pat, tok):
            return next(i for i, s in enumerate(stems, 1) if tok.startswith(s))
    return None


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


def split_day(tok):
    """`ostertag` -> ['oster', 'tag'], so that `2. Ostertag` can count the day of the feast.
    A bare `Tag` / `Feiertag` is the marker alone. Other words are left whole."""
    for suf in DAY_SUFFIXES:
        if tok == suf:
            return ['tag']
        if tok.endswith(suf) and tok[:-len(suf)] in DAY_STEMS:
            return [DAY_STEMS[tok[:-len(suf)]], 'tag']
    return [tok]


def starts(tok, prefixes):
    return any(tok.startswith(p) for p in prefixes)


def _advent1(year, cal):
    """Ordinal of the first Sunday of Advent: the fourth Sunday before Christmas Day."""
    xmas = to_ord(year, 12, 25, cal)
    return xmas - 1 - ((xmas - 1 - 6) % 7) - 21


class FeastError(ValueError):
    """The text names no feast, no year, or an impossible one (``Dom. 5. Adv.``), or
    carries a word or number the parser cannot account for (``2. Ostern``)."""


def _feasts(words):
    """{(kind, key): set of word indexes} for every feast any word names."""
    found = {}

    def add(key, i):
        found.setdefault(key, set()).add(i)

    for i, w in enumerate(words):
        if starts(w, TRIN):
            add(('trin', None), i)
        elif starts(w, ADV):
            add(('adv', None), i)
        elif starts(w, EPIPH):
            add(('epiph', None), i)
        else:
            for k, (prefixes, _off) in enumerate(EASTER_REL):
                if starts(w, prefixes):
                    add(('easter', k), i)
                    break
            else:
                for k, (prefixes, _md) in enumerate(FIXED):
                    if starts(w, [p for p in prefixes if ' ' not in p]):
                        add(('fixed', k), i)
                        break
    # Two-word names: `Mariae Verk.`, `Joh. Bapt.`
    for k, (prefixes, _md) in enumerate(FIXED):
        for p in prefixes:
            if ' ' in p:
                a, b = p.split(' ', 1)
                for i in range(len(words) - 1):
                    if words[i].startswith(a) and words[i + 1].startswith(b):
                        add(('fixed', k), i)
                        add(('fixed', k), i + 1)
    return found


def resolve(text, year=None, cal='P'):
    """``(ordinal, description)`` for a feast name. The year may be inside ``text``.

    Any number from 1500 to 1899 in the text is taken as the year; other numbers, Arabic
    or Roman, are the ordinal (``Dom. 9. Trin.``, ``Dom XXIII post Trin.``, ``Fer. 2.``).
    An ordinal before a German feast day counts the day of the feast: ``2. Ostertag`` and
    ``der dritte Pfingsttag`` are Easter Monday and Whit Tuesday.

    Raises :class:`FeastError` when nothing can be resolved, and when any word or number
    in the text is not accounted for, rather than resolve the rest and drop it.
    """
    toks = tokens(text)
    nums, words, last = [], [], False
    for w in toks:
        m = re.fullmatch(NUM_RE, w)
        if m:
            n = int(m.group(1))
            if 1500 <= n <= 1899:
                if year is not None and year != n:
                    raise FeastError('two years given: %d and %d' % (year, n))
                year = n
            else:
                nums.append(n)
            continue
        r = roman(w) or ord_word(w)
        if r is not None:
            nums.append(r)
            continue
        if re.fullmatch(LAST_RE, w):
            last = True
            continue
        for part in split_weekday(w):
            words.extend(split_day(part))
    if year is None:
        raise FeastError('no year: give one, e.g. "Dom. Palm. 1656"')
    if len(nums) + last > 1:
        raise FeastError('more than one ordinal in %r' % text)
    n = FEAST_DAYS if last else (nums[0] if nums else None)

    found = _feasts(words)
    if len(found) > 1:
        names = sorted({words[min(ix)] for ix in found.values()})
        raise FeastError('more than one feast named in %r: %s' % (text, ', '.join(names)))
    feria = [i for i, w in enumerate(words) if starts(w, FERIA)
             and not any(i in ix for ix in found.values())]
    post = [i for i, w in enumerate(words) if w in POST]
    tag = [i for i, w in enumerate(words) if w == 'tag']
    shift = [i for i, w in enumerate(words) if w in WEEKDAY_WORDS]
    check = [i for i, w in enumerate(words) if w in CHECK_WEEKDAY]
    used = set(feria) | set(tag) | set(check)
    for ix in found.values():
        used |= ix
    unknown = [w for i, w in enumerate(words)
               if i not in used and i not in post and i not in shift
               and w not in FILLER and not starts(w, FILLER_PREFIXES)]

    if not found:
        if n is not None and post:
            raise FeastError('"post" with no feast named: say which (Trin., Epiph.)')
        raise FeastError('no feast recognised in %r%s' % (
            text, ' (unrecognised: %s)' % ', '.join(unknown) if unknown else ''))
    if unknown:
        raise FeastError('unrecognised word%s in %r: %s' % (
            's' if len(unknown) > 1 else '', text, ', '.join(unknown)))
    (kind, key), = found

    def refuse_unless(ok, why):
        if not ok:
            raise FeastError('%s in %r' % (why, text))

    if last:
        refuse_unless(tag and not feria, '"letzter" names the last day of a feast (letzter Ostertag)')
    if feria:
        refuse_unless(n is not None, 'feria needs its number (Fer. 2. Pent.)')
        refuse_unless(1 <= n <= 7, 'feria counts the days of the week, 1 to 7, not %d' % n)
    if post:
        refuse_unless(kind in ('trin', 'epiph') and n is not None and not feria,
                      '"%s" belongs to a numbered Sunday after Trinity or Epiphany' % words[post[0]])
    if shift:
        refuse_unless(kind == 'easter' and not feria and not tag and n is None,
                      'a weekday after a feast needs a movable feast and no number')

    if kind == 'trin':
        refuse_unless(not tag, '"Tag" does not count the Sundays after Trinity')
        base = easter_of(year, cal) + 56
        if n is None or feria:
            o = base + ((n - 1) if feria else 0)
            what = 'Trinity Sunday' if n is None else 'Trinity feria %d' % n
        else:
            # The Sundays after Trinity run up to Advent: 22 to 27 of them, by the year.
            last_trin = (_advent1(year, cal) - 1 - base) // 7
            refuse_unless(1 <= n <= last_trin, 'there were %d Sundays after Trinity in %d, not %d'
                          % (last_trin, year, n))
            o, what = base + 7 * n, '%d. Sunday after Trinity' % n
    elif kind == 'adv':
        if n is None or not 1 <= n <= 4 or feria or tag:
            raise FeastError('Advent needs its Sunday, 1 to 4')
        o, what = _advent1(year, cal) + 7 * (n - 1), '%d. Sunday of Advent' % n
    elif kind == 'epiph':
        refuse_unless(not feria and not tag, 'a number with Epiphany counts the Sundays after it')
        epi = to_ord(year, 1, 6, cal)
        if n is None:
            o, what = epi, 'Epiphany'
        else:
            first = epi + 1 + ((6 - (epi + 1)) % 7)     # the first Sunday after 6 Jan
            # The Sundays after Epiphany run up to Septuagesima: 1 to 6 of them, by the year.
            last_epi = (easter_of(year, cal) - 63 - 1 - first) // 7 + 1
            refuse_unless(1 <= n <= last_epi, 'there were %d Sundays after Epiphany in %d, not %d'
                          % (last_epi, year, n))
            o, what = first + 7 * (n - 1), '%d. Sunday after Epiphany' % n
    else:
        if kind == 'easter':
            prefixes, off = EASTER_REL[key]
            o = easter_of(year, cal) + off
        else:
            prefixes, (m, d) = FIXED[key]
            o = to_ord(year, m, d, cal)
        hit = words[min(found[(kind, key)])] if kind == 'easter' else 'fixed feast %d %s' % (d, MON[m - 1])
        extra = 0
        if feria:
            refuse_unless(kind == 'easter', 'feria counts from a movable feast')
            extra = n - 1                           # feria 2 = Monday, 3 = Tuesday
        elif tag and n is not None:
            refuse_unless((kind, key) in DAY_FEASTS,
                          'only Ostertag, Pfingsttag and Weihnachtstag count their days')
            refuse_unless(1 <= n <= FEAST_DAYS, 'a feast was kept %d days at most' % FEAST_DAYS)
            extra = n - 1                           # 2. Ostertag = Monday
        elif n is not None:
            raise FeastError('the number %d is not used by %s in %r: a day of the feast is '
                             'written "%d. Ostertag" or "Fer. %d. Pasch."' % (n, hit, text, n, n))
        elif shift:
            extra = WEEKDAY_WORDS[words[shift[0]]]
        o += extra
        what = hit if not extra else '%s + %d day(s)' % (hit, extra)
        if last:
            what += ' (letzter = %d.)' % FEAST_DAYS
    for i in check:
        want = CHECK_WEEKDAY[words[i]]
        refuse_unless(o % 7 == want, '"%s", but %s is a %s' % (words[i], show(o, cal), DAY[o % 7]))
    return o, what


def feast_date(text, year=None, cal='P'):
    """``feast_date("Dom. Palm.", 1656)`` -> ``'Sun 30 Mar 1656 (Julian)'``."""
    return show(resolve(text, year, cal)[0], cal)
