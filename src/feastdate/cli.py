"""Command line: ``feastdate "Dom. Palm. 1656"`` -> ``Sun 30 Mar 1656 (Julian)``."""
import argparse
import re
import sys

from . import __version__
from .core import FeastError, easter_of, name_of, resolve, show, to_ord, week_of

EPILOG = """examples:
  feastdate "Dom. Palm. 1656"          Sun 30 Mar 1656 (Julian)
  feastdate "Dom. 9. Trin." 1657       the year may be a separate argument
  feastdate "Fer. 2. Pent." 1724       Whit Monday
  feastdate --easter 1744              Easter Sunday of that year
  feastdate --date 1657-07-26          the reverse: what the register called that day
  feastdate --gregorian "Dom. 1. Adv. 1650"   a Catholic parish

default calendar: Julian to 1699, the Protestant Improved Calendar from 1700.
a year inside the text is read only from 1500 to 1899; give any other year
(100 to 9999) as the last argument. --easter takes any year from 1 to 9999.
--date reads the date in the calendar in force on it: under the default,
Julian before 1 Mar 1700."""

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
    p.add_argument('--easter', metavar='YEAR', type=year_arg,
                   help='print Easter Sunday of YEAR')
    p.add_argument('--date', metavar='YYYY-MM-DD', type=date_arg,
                   help='name the church-year day of a date (the reverse lookup)')
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
        return print_names(*args.date, args.cal)
    if args.easter is not None:
        if args.text:
            p.error('--easter takes a year only')
        print('Easter %d = %s' % (args.easter, show(easter_of(args.easter, args.cal), args.cal)))
        return 0
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
    try:
        o, what = resolve(text, year, args.cal)
    except FeastError as e:
        msg = str(e)
        if (year is None and msg.startswith('no year') and len(words) > 1
                and re.fullmatch(r'\d{1,2}', words[-1].strip())):
            msg += ('\n(a separate year needs three digits or more, 100 to 9999; '
                    '%s is read as an ordinal)' % words[-1].strip())
        print('feastdate: %s' % msg, file=sys.stderr)
        return 2
    # The year the text already carries (resolve() refused any other) is not repeated.
    if year is None or re.search(r'(?<!\d)%d(?!\d)' % year, text):
        label = text
    else:
        label = '%s %d' % (text, year)
    print('%s = %s   [%s]' % (label, show(o, args.cal), what))
    return 0


def print_names(y, m, d, cal):
    """``26 Jul 1657 (Julian) = Sun   Dom. 9. p. Trin. (9th Sunday after Trinity)``."""
    if not 1 <= m <= 12:
        print('feastdate: no month %d in %d-%d-%d' % (m, y, m, d), file=sys.stderr)
        return 2
    try:
        names = name_of(y, m, d, cal)
        wd, week = week_of(y, m, d, cal)
    except FeastError as e:
        print('feastdate: %s' % e, file=sys.stderr)
        return 2
    day = show(to_ord(y, m, d, cal), cal)          # 'Sun 26 Jul 1657 (Julian)'
    if names:
        said = '; '.join('%s (%s)' % nm for nm in names)
    else:
        said = 'no name of its own: the week of %s' % week
    print('%s = %s   %s' % (day[4:], wd, said))
    return 0


if __name__ == '__main__':
    sys.exit(main())
