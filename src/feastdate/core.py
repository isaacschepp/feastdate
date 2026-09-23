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
    'j2o', 'o2j', 'g2o', 'o2g', 'to_ord', 'cal_of_year', 'is_leap',
    'fmt', 'show', 'resolve', 'feast_date', 'FeastError', 'name_of', 'week_of', 'ymd',
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


def is_leap(y, c):
    """Whether ``y`` is a leap year in calendar ``c`` (``'J'`` or ``'G'``)."""
    return y % 4 == 0 and (c == 'J' or y % 100 != 0 or y % 400 == 0)


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
# the same row. Longer, more specific prefixes come first. A prefix with a space is a
# two-word name, matched as described at FIXED.
#
# Every word of the text must be accounted for: a feast name, a number the feast uses, a
# weekday that agrees with the answer, or one of the connecting words below. Anything else
# is refused. A parser that skips what it does not understand answers "2. Ostertag" with
# Easter Sunday, a plausible date with nothing to say it is wrong.

EASTER_REL = [
    (('septuag',), -63),
    (('sexag',), -56),
    (('estomihi', 'esto', 'quinq', 'fastnacht'), -49),
    (('aschermittw', 'cinerum', 'ash wednes'), -46),
    (('invoc',), -42),
    (('reminisc',), -35),
    (('oculi',), -28),
    (('laetare', 'laet', 'lat'), -21),
    (('judica',), -14),
    (('palm',), -7),
    (('viridium', 'coena', 'cena', 'grundonnerstag', 'maundy'), -3),
    (('parasceve', 'karfreitag', 'charfreitag', 'good'), -2),
    # Before the Easter row, which `oster` would otherwise take: `Ostersamstag` is the
    # Saturday BEFORE Easter.
    (('karsamstag', 'charsamstag', 'karsonnabend', 'charsonnabend', 'ostersamstag',
      'ostersonnabend', 'oster samstag', 'oster sonnabend', 'sabbat sanct', 'holy sat'), -1),
    (('quasimod', 'quasi', 'quas', 'weisser'), 7),
    (('miseric', 'miser'), 14),
    (('jubil',), 21),
    (('cantat',), 28),
    (('rogat', 'voc'), 35),
    (('ascens', 'himmelfahrt'), 39),
    (('exaudi',), 42),
    (('pentecost', 'pent', 'pfingst', 'whit'), 49),
    # Catholic. Under 'P' it still resolves, to the same date.
    (('fronleichnam', 'corp christi'), 60),
    (('pasch', 'ostern', 'oster', 'easter'), 0),
]
TRIN = ('trinit', 'trin', 'dreifaltig')
# The last Sunday before Advent, as the Prussian church named it from 1816.
TOTEN = ('totensonnt', 'totenfest', 'ewigkeitssonnt')
TOTEN_FROM = 1816
ADV = ('advent', 'adv')
EPIPH = ('epiph',)
FERIA = ('feria', 'fer')
FERIA_DAY = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
# Weekday words English transcriptions use after a feast name: `Whit Monday`.
WEEKDAY_WORDS = {'monday': 1, 'tuesday': 2, 'montag': 1, 'dienstag': 2}
# Weekday words that only say which day the feast fell on. The answer must agree.
CHECK_WEEKDAY = {'sunday': 6, 'sonntag': 6, 'sonntags': 6, 'dominica': 6, 'dominicam': 6,
                 'dominicae': 6, 'saturday': 5, 'samstag': 5, 'sonnabend': 5, 'friday': 4,
                 'freitag': 4, 'thursday': 3, 'donnerstag': 3, 'wednesday': 2, 'mittwoch': 2}
# Fixed feasts, so the weekday can be asked too. (month, day).
#
# A prefix with a space is a two-word name. It matches the two words in order, with only
# connecting words between them (`Petri et Pauli`, `Inventio S. Crucis`), and it WINS over
# a one-word name on either of its words: `Nativ. Mariae` is 8 Sep, not Christmas, and
# `Mariae Himmelfahrt` is 15 Aug, not Ascension. Both orders are listed where registers
# write both (`Mariae Geburt`, `Nativitas Mariae`).
FIXED = [
    (('circumcis', 'neujahr'), (1, 1)),
    (('pauli bekehr', 'bekehr pauli', 'convers pauli', 'pauli convers'), (1, 25)),
    (('purif', 'lichtmess'), (2, 2)),
    # 25 Feb in a leap year: see LEAP_SHIFT.
    (('matthia', 'mathia'), (2, 24)),
    (('gregor',), (3, 12)),
    (('annunc', 'mari verk'), (3, 25)),
    (('georg',), (4, 23)),
    (('philipp jac', 'phil jac', 'walpurg'), (5, 1)),
    (('kreuzerfind', 'kreuz erfind', 'invent cruc', 'cruc invent'), (5, 3)),
    (('johannis', 'joh bapt'), (6, 24)),
    (('petri pauli', 'peter paul', 'pet paul'), (6, 29)),
    (('visitat', 'heimsuch'), (7, 2)),
    (('magdalen',), (7, 22)),
    (('jacob',), (7, 25)),
    (('laurent',), (8, 10)),
    (('assumpt', 'mari himmelf', 'himmelf mari'), (8, 15)),
    (('bartholom',), (8, 24)),
    (('nativ mari', 'mari nativ', 'mari geburt', 'geburt mari'), (9, 8)),
    (('kreuzerhoh', 'kreuz erhoh', 'exalt cruc', 'cruc exalt'), (9, 14)),
    (('matthae', 'matthai', 'matthau', 'mathae', 'mathai'), (9, 21)),
    (('michael',), (9, 29)),
    (('galli', 'gallus'), (10, 16)),
    (('simon jud', 'sim jud'), (10, 28)),
    (('omnium sanct', 'allerheilig'), (11, 1)),
    (('omnium anim', 'allerseel'), (11, 2)),
    (('martini',), (11, 11)),
    (('elisab',), (11, 19)),
    (('andreae', 'andreas'), (11, 30)),
    (('thomae', 'thomas'), (12, 21)),
    (('nativ', 'christtag', 'weihnacht', 'christmas'), (12, 25)),
    (('stephan',), (12, 26)),
    (('johannis evang', 'joh evang'), (12, 27)),
    (('innocent', 'unschuld', 'kindlein'), (12, 28)),
]
# A feast from 24 to 28 Feb moves one day later in a leap year. The Julian leap day was
# counted in by doubling 24 Feb (the bissextile), so the feasts after it slid a day, and
# the German almanacs, Protestant and Catholic, went on keeping Matthias on 25 Feb in a
# leap year long after 1700. The leap year is the one of the calendar in force that day.
LEAP_SHIFT = ((2, 24), (2, 28))
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
             (r'(?:prim|secund|terti|quart|quint|sext|septim)(?:a|o|ae|am|us|um|i)?',
              ('prim', 'secund', 'terti', 'quart', 'quint', 'sext', 'septim')),
             (r'(?:first|second|third|fourth)', ('first', 'second', 'third', 'fourth'))]
# `letzter Ostertag` is the last day of a feast; `Dom. ult. p. Trin.` and `letzter Sonntag
# nach Trinitatis` the last Sunday after Trinity (or Pentecost), the one before Advent.
LAST_RE = r'letzt(?:e|er|en|es|em)?|ult(?:im(?:a|o|am|ae|us|um|i))?'
# Words that connect a feast name to the rest of the entry and add nothing to the date.
FILLER = {'dom', 'dni', 'die', 'dies', 'festo', 'festum', 'fest', 'festi', 'feast', 'day',
          'in', 'am', 'an', 'den', 'der', 'dem', 'des', 'd', 'the', 'of', 'war', 'als', 'ipso',
          'mariae', 'maria', 'marie', 'christi', 's', 'st', 'sancti', 'sankt', 'heil', 'hl',
          'heiligen', 'mihi', 'geniti', 'et', 'und'}
# The saint's epithet: `Andreae Apost.`, `Michaelis Archangeli`. `evang` is one too, except
# in `Johannis Evang.`, where the two-word name takes it first.
FILLER_PREFIXES = ('domin', 'jucund', 'bapt', 'apost', 'evang', 'archang', 'martyr', 'virg',
                   'episc')
# A day counted from a feast: `Dom. 5. p. Epiph.`, `Freitag nach Jubilate`, `Dom. ante
# Nativ.`. The day comes before the word and the feast after it.
POST = {'post', 'p', 'after', 'nach'}
ANTE = {'ante', 'vor', 'before'}
# `Dom.` names the Sunday only in front of `post` / `ante`. Everywhere else it is filler.
DOM = 'dom'
# The most Sundays counted after Easter: `Dom. 6. post Pascha` is Exaudi.
EASTER_SUNDAYS = 6
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

    def filler(w):
        return w in FILLER or starts(w, FILLER_PREFIXES)

    # Two-word names first (`Mariae Verk.`, `Joh. Bapt.`, `Petri et Pauli`). The words they
    # take are not read again on their own, so `Nativ. Mariae` is not also Christmas.
    taken = set()
    for kind, table in (('easter', EASTER_REL), ('fixed', FIXED)):
        for k, (prefixes, _when) in enumerate(table):
            for p in prefixes:
                if ' ' not in p:
                    continue
                a, b = p.split(' ', 1)
                for i, w in enumerate(words):
                    if not w.startswith(a):
                        continue
                    for j in range(i + 1, len(words)):
                        if words[j].startswith(b):
                            add((kind, k), i)
                            add((kind, k), j)
                            taken.update((i, j))
                            break
                        if not filler(words[j]):
                            break

    for i, w in enumerate(words):
        if i in taken:
            continue
        if starts(w, TOTEN):
            add(('toten', None), i)
        elif starts(w, TRIN):
            add(('trin', None), i)
        elif starts(w, ADV):
            add(('adv', None), i)
        elif starts(w, EPIPH):
            add(('epiph', None), i)
        else:
            for k, (prefixes, _off) in enumerate(EASTER_REL):
                if starts(w, [p for p in prefixes if ' ' not in p]):
                    add(('easter', k), i)
                    break
            else:
                for k, (prefixes, _md) in enumerate(FIXED):
                    if starts(w, [p for p in prefixes if ' ' not in p]):
                        add(('fixed', k), i)
                        break
    return found


def resolve(text, year=None, cal='P'):
    """``(ordinal, description)`` for a feast name. The year may be inside ``text``.

    Any number from 1500 to 1899 in the text is taken as the year; other numbers, Arabic
    or Roman, are the ordinal (``Dom. 9. Trin.``, ``Dom XXIII post Trin.``, ``Fer. 2.``).
    An ordinal before a German feast day counts the day of the feast: ``2. Ostertag`` and
    ``der dritte Pfingsttag`` are Easter Monday and Whit Tuesday. A day named before
    ``post`` / ``nach`` / ``vor`` / ``ante`` is counted from the feast after it, strictly:
    ``Freitag nach Jubilate``, ``Dom. p. Nativ.``, ``Sonnabend vor Palmarum``. The Catholic
    ``Dom. 5. post Pent.`` counts Sundays from Pentecost, and ``Dom. ult. p. Trin.`` is the
    last Sunday before Advent.

    Raises :class:`FeastError` when nothing can be resolved, and when any word or number
    in the text is not accounted for, rather than resolve the rest and drop it.
    """
    toks = tokens(text)
    nums, words, last = [], [], False
    last_word = None
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
            last, last_word = True, w
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
    post = [i for i, w in enumerate(words) if w in POST or w in ANTE]
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
            raise FeastError('"post" with no feast named: say which (Trin., Pent., Epiph.)')
        raise FeastError('no feast recognised in %r%s' % (
            text, ' (unrecognised: %s)' % ', '.join(unknown) if unknown else ''))
    if unknown:
        raise FeastError('unrecognised word%s in %r: %s' % (
            's' if len(unknown) > 1 else '', text, ', '.join(unknown)))
    (kind, key), = found

    def refuse_unless(ok, why):
        if not ok:
            raise FeastError('%s in %r' % (why, text))

    pent = kind == 'easter' and EASTER_REL[key][1] == 49
    # `Dom. ult. p. Trin.`, `letzter Sonntag nach Trinitatis`, `Dom. ult. Trin.`: the last
    # Sunday after Trinity or Pentecost, the one before Advent. `letzter Ostertag` is not.
    ultimo = last and not tag and (bool(post) or kind == 'trin')
    if last and not ultimo:
        refuse_unless(tag and not feria, '"%s" names the last day of a feast (letzter Ostertag) '
                      'or the last Sunday after Trinity (Dom. ult. p. Trin.)' % last_word)
    if ultimo:
        refuse_unless(kind == 'trin' or pent, '"%s" counts the last Sunday after Trinity or '
                      'Pentecost only' % last_word)
        refuse_unless(not feria, '"%s" names a Sunday, not a feria' % last_word)
        n = None
    if feria:
        refuse_unless(n is not None, 'feria needs its number (Fer. 2. Pent.)')
        refuse_unless(1 <= n <= 7, 'feria counts the days of the week, 1 to 7, not %d' % n)
    # A day counted from the feast: the target day stands before `post` / `nach` / `vor`,
    # the feast after it. A weekday word before the relation word is the TARGET, not a
    # check; one after it still checks, or moves, the feast (`Freitag nach Ostermontag`).
    target, count, ante, numbered = None, None, False, False
    if len(post) > 1:
        raise FeastError('more than one of %s in %r: one day counted from one feast'
                         % (', '.join('"%s"' % words[i] for i in post), text))
    if post:
        r = post[0]
        rel, ante = words[r], words[r] in ANTE
        refuse_unless(min(found[(kind, key)]) > r, 'the feast goes after "%s"' % rel)
        refuse_unless(all(i < r for i in feria), 'the feria goes before "%s"' % rel)
        days = {CHECK_WEEKDAY[words[i]] for i in check if i < r}
        days |= {WEEKDAY_WORDS[words[i]] - 1 for i in shift if i < r}
        if feria:
            days.add((n - 2) % 7)                   # feria 1 = Sunday, 2 = Monday
        if not days and DOM in words[:r]:
            days = {6}
        refuse_unless(len(days) <= 1, 'two different days named before "%s"' % rel)
        target = days.pop() if days else None
        check = [i for i in check if i > r]
        shift = [i for i in shift if i > r]
        if ultimo:
            refuse_unless(not ante and target == 6 and not shift,
                          '"%s ... %s" is the last Sunday after the feast: Dom. ult. p. Trin.'
                          % (last_word, rel))
            target = None
        # `Dom. 5. p. Epiph.`, `Dom XXIII post Trin.`: the numbered Sundays, counted below.
        numbered = (kind in ('trin', 'epiph') and n is not None and not ante and not feria
                    and target in (None, 6))
        if not numbered and not ultimo:
            refuse_unless(target is not None, '"%s" needs the day it counts: Dom., Freitag, '
                          'Feria 6' % rel)
            if feria:
                feria, n = [], None                 # the number was the feria's
            elif kind != 'adv' and not tag:
                count, n = n, None                  # `Dom. 2. p. Pasch.`: the 2nd Sunday
        if count is not None:
            refuse_unless(target == 6, 'a number before "%s" counts Sundays, not %ss'
                          % (rel, FERIA_DAY[target]))
            refuse_unless(not ante and kind == 'easter' and EASTER_REL[key][1] in (0, 49),
                          'only Easter, Pentecost, Trinity and Epiphany number the Sundays '
                          'after them')
            if pent:
                # The Catholic count: `Dom. 1. post Pent.` is Trinity Sunday, and the Sundays
                # run up to Advent, 23 to 28 of them, one more than the Trinity count.
                whit = easter_of(year, cal) + 49
                last_pent = (_advent1(year, cal) - 1 - whit) // 7
                refuse_unless(1 <= count <= last_pent, 'there were %d Sundays after Pentecost in '
                              '%d, not %d' % (last_pent, year, count))
            else:
                refuse_unless(1 <= count <= EASTER_SUNDAYS, 'Sundays after Easter run 1 to %d, '
                              'not %d' % (EASTER_SUNDAYS, count))
    if shift:
        refuse_unless(kind == 'easter' and not feria and not tag and n is None,
                      'a weekday after a feast needs a movable feast and no number')
        # `Whit Monday` counts from a Sunday. After a weekday feast the count is nonsense:
        # `Karfreitag Montag` would be a Saturday.
        refuse_unless(EASTER_REL[key][1] % 7 == 0,
                      '"%s" counts from a Sunday feast' % words[shift[0]])

    if ultimo:
        o = _advent1(year, cal) - 7
        what = 'last Sunday after %s' % ('Pentecost' if pent else 'Trinity')
    elif kind == 'toten':
        refuse_unless(year >= TOTEN_FROM, '%s was ordered in Prussia in %d; before it the Sunday '
                      'is "Dom. ult. p. Trin."' % (words[min(found[(kind, key)])], TOTEN_FROM))
        refuse_unless(n is None and not feria and not tag,
                      'a number is not used by %s' % words[min(found[(kind, key)])])
        o, what = _advent1(year, cal) - 7, 'Totensonntag, the last Sunday before Advent'
    elif kind == 'trin':
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
            leap = (LEAP_SHIFT[0] <= (m, d) <= LEAP_SHIFT[1]
                    and is_leap(year, cal_of_year(year, cal, m, d)))
            d += leap
            o = to_ord(year, m, d, cal)
        hit = (words[min(found[(kind, key)])] if kind == 'easter' else
               'fixed feast %d %s%s' % (d, MON[m - 1], ', leap year' if leap else ''))
        extra = 0
        if feria:
            refuse_unless(kind == 'easter', 'feria counts from a movable feast')
            if off % 7:
                # A weekday feast: `Feria 6 in Parasceve` is Good Friday itself. The number
                # names the feast's own weekday (feria 1 = Sunday), so it is a check.
                refuse_unless((n - 2) % 7 == o % 7, 'feria %d does not fall on %s, a %s'
                              % (n, hit, FERIA_DAY[o % 7]))
            else:
                extra = n - 1                       # feria 2 = Monday, 3 = Tuesday
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
    if target is not None and not numbered:
        # Strictly after, or strictly before: the Sunday after Michaelmas, when 29 Sep is
        # itself a Sunday, is 6 Oct, as with the first Sunday after Epiphany.
        if ante:
            o -= 1 + (o - 1 - target) % 7
        else:
            o += 1 + (target - o - 1) % 7 + 7 * ((count or 1) - 1)
        what = '%s%s %s %s' % ('%d. ' % count if count else '', FERIA_DAY[target],
                               'before' if ante else 'after', what)
    return o, what


def feast_date(text, year=None, cal='P'):
    """``feast_date("Dom. Palm.", 1656)`` -> ``'Sun 30 Mar 1656 (Julian)'``."""
    return show(resolve(text, year, cal)[0], cal)


# ---------------------------------------------------------------------------------------
# The reverse lookup: a date -> the names a register gives that day.
#
# Every name below is written in a form resolve() reads back to the same day, and the test
# suite checks that for every day of 1600 to 1799 in all three calendars. A name added here
# that resolve() reads differently fails that test rather than drifting in silence.

#: Movable days by offset from Easter Sunday: (canonical name, English gloss).
REV_EASTER = {
    -63: ('Dom. Septuagesimae', 'Septuagesima'),
    -56: ('Dom. Sexagesimae', 'Sexagesima'),
    -49: ('Dom. Estomihi', 'Estomihi, Quinquagesima'),
    -46: ('Dies Cinerum', 'Ash Wednesday'),
    -42: ('Dom. Invocavit', 'Invocavit, 1st Sunday in Lent'),
    -35: ('Dom. Reminiscere', 'Reminiscere, 2nd Sunday in Lent'),
    -28: ('Dom. Oculi', 'Oculi, 3rd Sunday in Lent'),
    -21: ('Dom. Laetare', 'Laetare, 4th Sunday in Lent'),
    -14: ('Dom. Judica', 'Judica, 5th Sunday in Lent'),
    -7: ('Dom. Palmarum', 'Palm Sunday'),
    -3: ('Die Viridium', 'Maundy Thursday'),
    -2: ('Parasceve', 'Good Friday'),
    -1: ('Sabbatum Sanctum', 'Holy Saturday'),
    0: ('Pascha', 'Easter Sunday'),
    1: ('Fer. 2. Pasch.', 'Easter Monday'),
    2: ('Fer. 3. Pasch.', 'Easter Tuesday'),
    7: ('Dom. Quasimodogeniti', 'Quasimodogeniti, 1st Sunday after Easter'),
    14: ('Dom. Misericordias Domini', 'Misericordias Domini, 2nd Sunday after Easter'),
    21: ('Dom. Jubilate', 'Jubilate, 3rd Sunday after Easter'),
    28: ('Dom. Cantate', 'Cantate, 4th Sunday after Easter'),
    35: ('Dom. Rogate', 'Rogate, 5th Sunday after Easter'),
    39: ('Ascensio Domini', 'Ascension Day'),
    42: ('Dom. Exaudi', 'Exaudi, Sunday after Ascension'),
    49: ('Pentecoste', 'Whit Sunday'),
    50: ('Fer. 2. Pent.', 'Whit Monday'),
    51: ('Fer. 3. Pent.', 'Whit Tuesday'),
    56: ('Dom. Trinitatis', 'Trinity Sunday'),
}
#: Corpus Christi is Catholic, so it is named only under ``'G'``.
REV_CORPUS = (60, 'Corpus Christi', 'Corpus Christi')
#: The Sundays a weekday is counted from, ``Feria 4 post Jubilate``, by offset from Easter.
REV_POST = {-63: 'Septuagesimam', -56: 'Sexagesimam', -49: 'Estomihi', -42: 'Invocavit',
            -35: 'Reminiscere', -28: 'Oculi', -21: 'Laetare', -14: 'Judica', -7: 'Palmarum',
            0: 'Pascha', 7: 'Quasimodogeniti', 14: 'Misericordias Domini', 21: 'Jubilate',
            28: 'Cantate', 35: 'Rogate', 42: 'Exaudi', 49: 'Pentecosten', 56: 'Trinitatis'}
#: Weekdays with a name of their own that is still written as a feria.
REV_WEEKDAY_GLOSS = {-47: 'Shrove Tuesday'}
#: Fixed feasts by (month, day): (canonical name, English gloss). 24 Feb moves to 25 Feb in
#: a leap year (LEAP_SHIFT), as resolve() moves it.
REV_FIXED = {
    (1, 1): ('Circumcisio Domini', 'New Year, the Circumcision'),
    (1, 6): ('Epiphania Domini', 'Epiphany'),
    (1, 25): ('Conversio Pauli', 'Conversion of St Paul'),
    (2, 2): ('Purificatio Mariae', 'Candlemas'),
    (2, 24): ('Matthiae', 'St Matthias'),
    (3, 12): ('Gregorii', 'St Gregory'),
    (3, 25): ('Annunciatio Mariae', 'Lady Day, the Annunciation'),
    (4, 23): ('Georgii', 'St George'),
    (5, 1): ('Philippi et Jacobi', 'SS Philip and James'),
    (5, 3): ('Inventio Crucis', 'Finding of the Cross'),
    (6, 24): ('Johannis Baptistae', 'St John the Baptist'),
    (6, 29): ('Petri et Pauli', 'SS Peter and Paul'),
    (7, 2): ('Visitatio Mariae', 'Visitation'),
    (7, 22): ('Mariae Magdalenae', 'St Mary Magdalene'),
    (7, 25): ('Jacobi', 'St James'),
    (8, 10): ('Laurentii', 'St Lawrence'),
    (8, 15): ('Assumptio Mariae', 'Assumption'),
    (8, 24): ('Bartholomaei', 'St Bartholomew'),
    (9, 8): ('Nativitas Mariae', 'Nativity of Mary'),
    (9, 14): ('Exaltatio Crucis', 'Exaltation of the Cross'),
    (9, 21): ('Matthaei', 'St Matthew'),
    (9, 29): ('Michaelis', 'Michaelmas'),
    (10, 16): ('Galli', 'St Gall'),
    (10, 28): ('Simonis et Judae', 'SS Simon and Jude'),
    (11, 1): ('Omnium Sanctorum', 'All Saints'),
    (11, 2): ('Omnium Animarum', 'All Souls'),
    (11, 11): ('Martini', 'Martinmas'),
    (11, 19): ('Elisabethae', 'St Elizabeth'),
    (11, 30): ('Andreae', 'St Andrew'),
    (12, 21): ('Thomae', 'St Thomas'),
    (12, 25): ('Nativitas Christi', 'Christmas Day'),
    (12, 26): ('Stephani', 'St Stephen, 2nd day of Christmas'),
    (12, 27): ('Johannis Evangelistae', 'St John the Evangelist'),
    (12, 28): ('Innocentium', 'Holy Innocents'),
}


def _nth(n):
    """1 -> '1st', 22 -> '22nd', 12 -> '12th'."""
    suf = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return '%d%s' % (n, suf)


def ymd(o, cal):
    """An ordinal -> ``(y, m, d)`` in the calendar in force on that day, as :func:`show`."""
    return o2g(o) if cal == 'G' or (cal == 'P' and o >= SWITCH) else o2j(o)


def name_of(y, m, d, cal='P'):
    """Every church-year name for a day: ``[(name, gloss), ...]``, movable days first.

    The date is read in the calendar in force on it, as :func:`to_ord` reads it: under
    ``'P'`` Julian before 1 Mar 1700. Each name resolves back to the same day with
    :func:`resolve`, the same year and the same calendar::

        >>> name_of(1657, 7, 26)
        [('Dom. 9. p. Trin.', '9th Sunday after Trinity')]

    A day can have several names (``Dom. 1. Adv.`` and ``Andreae``) or none: a weekday
    outside the weeks from Septuagesima to Trinity is dated by the day of the month, and
    has only its saint's day if it has one. :func:`week_of` says which week it is in.

    Raises :class:`FeastError` for a day that does not exist in that calendar.
    """
    o = to_ord(y, m, d, cal)
    wd = o % 7
    e = easter_of(y, cal)
    k = o - e
    out = []

    # The Easter cycle, Septuagesima to the week of Trinity.
    if k in REV_EASTER:
        out.append(REV_EASTER[k])
    elif cal == 'G' and k == REV_CORPUS[0]:
        out.append(REV_CORPUS[1:])
    elif wd != 6 and k - (wd + 1) in REV_POST:
        sun = REV_POST[k - (wd + 1)]
        gloss = '%s after %s' % (FERIA_DAY[wd], REV_EASTER[k - (wd + 1)][1].split(',')[0]
                                        .replace('Easter Sunday', 'Easter'))
        if k in REV_WEEKDAY_GLOSS:
            gloss = '%s, %s' % (REV_WEEKDAY_GLOSS[k], gloss)
        out.append(('Feria %d post %s' % (wd + 2, sun), gloss))

    if wd == 6:
        adv1 = _advent1(y, cal)
        trin = e + 56
        if trin < o < adv1:
            n = (o - trin) // 7
            out.append(('Dom. %d. p. Trin.' % n, '%s Sunday after Trinity' % _nth(n)))
            if cal == 'G':
                out.append(('Dom. %d. p. Pent.' % (n + 1),
                            '%s Sunday after Pentecost' % _nth(n + 1)))
            if o == adv1 - 7:
                out.append(('Dom. ult. p. Trin.', 'last Sunday after Trinity'))
                if cal == 'G':
                    out.append(('Dom. ult. p. Pent.', 'last Sunday after Pentecost'))
                if cal == 'P' and y >= TOTEN_FROM:
                    out.append(('Totensonntag', 'Sunday of the Dead, the last before Advent'))
        elif adv1 <= o < adv1 + 28:
            n = (o - adv1) // 7 + 1
            out.append(('Dom. %d. Adv.' % n, '%s Sunday of Advent' % _nth(n)))
        epi = to_ord(y, 1, 6, cal)
        first = epi + 1 + ((6 - (epi + 1)) % 7)
        if first <= o < e - 63:
            n = (o - first) // 7 + 1
            out.append(('Dom. %d. p. Epiph.' % n, '%s Sunday after Epiphany' % _nth(n)))
        if m == 12 and d >= 26:
            out.append(('Dom. p. Nativ.', 'Sunday after Christmas'))
        if m == 1 and 2 <= d <= 5:
            out.append(('Dom. p. Circumcis.', 'Sunday after New Year'))

    # Fixed feasts. The leap shift is decided in the calendar in force on the feast.
    for (fm, fd), named in REV_FIXED.items():
        if LEAP_SHIFT[0] <= (fm, fd) <= LEAP_SHIFT[1] and is_leap(y, cal_of_year(y, cal, fm, fd)):
            fd += 1
        if (fm, fd) == (m, d):
            out.append(named)
            break
    return out


def week_of(y, m, d, cal='P'):
    """``(weekday, name of the Sunday that begins the day's week)``.

    ``week_of(1657, 7, 28)`` -> ``('Tue', 'Dom. 9. p. Trin.')``. A description, not a name
    a register used: ``Feria 3 post Dom. 9. p. Trin.`` does not resolve, because a feria is
    counted only from a Sunday that carries no number.
    """
    o = to_ord(y, m, d, cal)
    sun = o - (o % 7 + 1) % 7
    names = name_of(*ymd(sun, cal), cal)
    return DAY[o % 7], (names[0][0] if names else None)
