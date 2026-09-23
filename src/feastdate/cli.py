"""Command line: ``feastdate "Dom. Palm. 1656"`` -> ``Sun 30 Mar 1656 (Julian)``."""
import argparse
import json
import re
import sys

from . import __version__
from .core import (DAY, SWITCHES, FeastError, calendar_of, easter_of, is_greg, name_of,
                   resolve, show, to_ord, week_of, ymd)

EPILOG = """examples:
  feastdate "Dom. Palm. 1656"          Sun 30 Mar 1656 (Julian)
  feastdate "Dom. 9. Trin." 1657       the year may be a separate argument
  feastdate "Fer. 2. Pent." 1724       Whit Monday
  feastdate --easter 1744              Easter Sunday of that year
  feastdate --date 1657-07-26          the reverse: what the register called that day
  feastdate --gregorian "Dom. 1. Adv. 1650"   a Catholic parish
  feastdate --switch england "Michaelis 1752"  the British switch of Sep 1752
  feastdate --switch 1610-08-22:1610-09-02 --easter 1610   any switch, given as its two days
  feastdate --iso "Dom. Palm. 1656"    1656-03-30 J
  feastdate --json - < entries.txt     one entry per line in, one JSON object per line out

batch input (-, or no text while stdin is redirected): one entry per line, with an
optional year column after a tab ("Dom. 9. Trin.<TAB>1950"). A refused line still
gives a line of output; the exit status is 0 only if every line resolved.

default calendar: Julian to 1699, the Protestant Improved Calendar from 1700.
a year inside the text is read only from 1500 to 1899; give any other year
(100 to 9999) as the last argument. --easter takes any year from 1 to 9999.
--date reads the date in the calendar in force on it: under the default,
Julian before 1 Mar 1700.

--switch takes a territory:
  %s
or the last Julian day and the first Gregorian day, LAST:FIRST
(1752-09-02:1752-09-14). Easter is Julian before the switch, Gregorian after.""" % ', '.join(
    SWITCHES)

YEAR_MIN, YEAR_MAX = 1, 9999


def year_arg(s):
    """argparse type for a year: the same range on every route into the calendar."""
    try:
        y = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError('not a year: %r' % s)
    if not YEAR_MIN <= y <= YEAR_MAX:
        raise argparse.ArgumentTypeError('year %d is outside %d to %d' % (y, YEAR_MIN, YEAR_MAX))
    return y


def date_arg(s):
    """argparse type for ``--date``: ``YYYY-MM-DD``, not yet checked against a calendar."""
    m = re.fullmatch(r'(\d{1,4})-(\d{1,2})-(\d{1,2})', s.strip())
    if not m:
        raise argparse.ArgumentTypeError('not a date: %r (write it YYYY-MM-DD)' % s)
    y = year_arg(m.group(1))
    return y, int(m.group(2)), int(m.group(3))


def switch_arg(s):
    """argparse type for ``--switch``: a preset name or ``LAST-JULIAN:FIRST-GREGORIAN``."""
    try:
        return calendar_of(s)
    except FeastError as e:
        raise argparse.ArgumentTypeError(str(e))


def build_parser():
    p = argparse.ArgumentParser(
        prog='feastdate',
        description='Convert a church-year feast name and year into a calendar date.',
        epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('text', nargs='*', help='feast name and year, e.g. "Dom. 9. Trin. 1657"')
    cal = p.add_mutually_exclusive_group()
    cal.add_argument('--gregorian', dest='cal', action='store_const', const='G',
                     help='Gregorian throughout (Catholic parishes)')
    cal.add_argument('--julian', dest='cal', action='store_const', const='J',
                     help='Julian throughout')
    cal.add_argument('--switch', dest='cal', metavar='TERRITORY', type=switch_arg,
                     help='the Julian-to-Gregorian switch of a territory (england, sweden, '
                          '...) or LAST:FIRST, e.g. 1752-09-02:1752-09-14')
    p.add_argument('--easter', metavar='YEAR', type=year_arg,
                   help='print Easter Sunday of YEAR')
    p.add_argument('--date', metavar='YYYY-MM-DD', type=date_arg,
                   help='name the church-year day of a date (the reverse lookup)')
    out = p.add_mutually_exclusive_group()
    out.add_argument('--iso', dest='fmt', action='store_const', const='iso',
                     help='print only the date and J or G: 1656-03-30 J')
    out.add_argument('--json', dest='fmt', action='store_const', const='json',
                     help='print one JSON object per entry')
    p.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    p.set_defaults(cal='P')
    return p


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    p = build_parser()
    args = p.parse_args(argv)
    if args.date is not None:
        if args.text or args.easter is not None:
            p.error('--date takes a date only')
        if args.fmt == 'iso':
            p.error('--date prints names, not a date: use --json')
        return print_names(*args.date, args.cal, args.fmt)
    if args.easter is not None:
        if args.text:
            p.error('--easter takes a year only')
        try:
            o = easter_of(args.easter, args.cal)
        except FeastError as e:
            if args.fmt == 'json':
                print(json.dumps({'input': 'Easter %d' % args.easter, 'error': str(e)},
                                 ensure_ascii=False))
            else:
                print('feastdate: %s' % e, file=sys.stderr)
            return 2
        if args.fmt:
            print(render(args.fmt, 'Easter %d' % args.easter, o, 'easter', args.cal))
        else:
            print('Easter %d = %s' % (args.easter, show(o, args.cal)))
        return 0
    if args.text == ['-'] or (not args.text and not _stdin_is_tty()):
        return run_batch(sys.stdin, args.cal, args.fmt)
    if not args.text:
        p.print_help()
        return 2
    words, year = list(args.text), None
    # A separate trailing year is passed as the year, not left to resolve()'s in-text
    # 1500-1899 window, so "feastdate 'Dom. 9. Trin.' 1950" works. Ordinals never reach
    # three digits, so a three-digit-or-longer last word is always a year. A shorter one
    # stays an ordinal: read as a year, "Dom. Trin." 9 would answer for AD 9 in silence.
    if len(words) > 1 and re.fullmatch(r'\d{3,}', words[-1].strip()):
        try:
            year = year_arg(words.pop())
        except argparse.ArgumentTypeError as e:
            p.error(str(e))
    text = ' '.join(words)
    given = ' '.join(args.text)
    try:
        o, what = resolve(text, year, args.cal)
    except FeastError as e:
        msg = str(e)
        if (year is None and msg.startswith('no year') and len(words) > 1
                and re.fullmatch(r'\d{1,2}', words[-1].strip())):
            msg += ('\n(a separate year needs three digits or more, 100 to 9999; '
                    '%s is read as an ordinal)' % words[-1].strip())
        if args.fmt == 'json':
            print(json.dumps({'input': given, 'error': msg}, ensure_ascii=False))
        else:
            print('feastdate: %s' % msg, file=sys.stderr)
        return 2
    print(render(args.fmt, given, o, what, args.cal, label(text, year)))
    return 0


def label(text, year):
    """The entry as the output line repeats it. The year the text already carries
    (resolve() refused any other) is not repeated."""
    if year is None or re.search(r'(?<!\d)%d(?!\d)' % year, text):
        return text
    return '%s %d' % (text, year)


def render(fmt, given, o, what, cal, text=None):
    """One resolved entry as a line of output: ``fmt`` is None, ``'iso'`` or ``'json'``.

    ``given`` is the input as it came in, for ``--json``. ``text`` is the label the
    default line starts with.
    """
    greg = cal_greg(o, cal)
    iso = '%04d-%02d-%02d' % ymd(o, cal)
    if fmt == 'iso':
        return '%s %s' % (iso, 'G' if greg else 'J')
    if fmt == 'json':
        return json.dumps({'input': given, 'date': iso,
                           'calendar': 'Gregorian' if greg else 'Julian',
                           'weekday': DAY[o % 7], 'jdn': o, 'parsed': what},
                          ensure_ascii=False)
    return '%s = %s   [%s]' % (text, show(o, cal), what)


def cal_greg(o, cal):
    """Whether ``o`` is printed in the Gregorian calendar, the rule :func:`show` uses."""
    return is_greg(o, cal)


def _stdin_is_tty():
    """True when stdin is a terminal, or absent: then there is nothing to read in batch."""
    try:
        return sys.stdin is None or sys.stdin.isatty()
    except (AttributeError, ValueError, OSError):
        return True


def run_batch(stream, cal, fmt):
    """Resolve one entry per line of ``stream``: ``text``, or ``text<TAB>year``.

    Every input line gives exactly one output line, a refused one included, so the
    output lines up with the input. A refusal is also reported on stderr with its line
    number. Returns 0 if every line resolved, 2 otherwise.
    """
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8-sig', errors='replace')
    status = 0
    for n, line in enumerate(stream, 1):
        line = line.rstrip('\r\n')
        text, _tab, ycol = line.partition('\t')
        text, ycol = text.strip(), ycol.strip()
        try:
            if not text:
                raise FeastError('empty line')
            year = None
            if ycol:
                try:
                    year = year_arg(ycol)
                except argparse.ArgumentTypeError as e:
                    raise FeastError(str(e))
            o, what = resolve(text, year, cal)
        except FeastError as e:
            status = 2
            msg = ' '.join(str(e).split())
            print('feastdate: line %d: %s' % (n, msg), file=sys.stderr)
            if fmt == 'json':
                print(json.dumps({'input': line, 'error': msg}, ensure_ascii=False))
            elif fmt == 'iso':
                print('error: %s' % msg)
            else:
                print('%s = error: %s' % (text, msg))
            continue
        print(render(fmt, line, o, what, cal, label(text, year)))
    return status


def print_names(y, m, d, cal, fmt=None):
    """``26 Jul 1657 (Julian) = Sun   Dom. 9. p. Trin. (9th Sunday after Trinity)``."""
    given = '%04d-%02d-%02d' % (y, m, d)
    try:
        if not 1 <= m <= 12:
            raise FeastError('no month %d in %d-%d-%d' % (m, y, m, d))
        names = name_of(y, m, d, cal)
        wd, week = week_of(y, m, d, cal)
    except FeastError as e:
        if fmt == 'json':
            print(json.dumps({'input': given, 'error': str(e)}, ensure_ascii=False))
        else:
            print('feastdate: %s' % e, file=sys.stderr)
        return 2
    if fmt == 'json':
        o = to_ord(y, m, d, cal)
        print(json.dumps({'input': given, 'date': given,
                          'calendar': 'Gregorian' if cal_greg(o, cal) else 'Julian',
                          'weekday': wd, 'jdn': o,
                          'names': [{'name': nm, 'gloss': gl} for nm, gl in names],
                          'week': week}, ensure_ascii=False))
        return 0
    day = show(to_ord(y, m, d, cal), cal)          # 'Sun 26 Jul 1657 (Julian)'
    if names:
        said = '; '.join('%s (%s)' % nm for nm in names)
    else:
        said = 'no name of its own: the week of %s' % week
    print('%s = %s   %s' % (day[4:], wd, said))
    return 0


if __name__ == '__main__':
    sys.exit(main())
