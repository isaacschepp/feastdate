"""Command line: ``feastdate "Dom. Palm. 1656"`` -> ``Sun 30 Mar 1656 (Julian)``."""
import argparse
import re
import sys

from . import __version__
from .core import FeastError, easter_of, resolve, show

EPILOG = """examples:
  feastdate "Dom. Palm. 1656"          Sun 30 Mar 1656 (Julian)
  feastdate "Dom. 9. Trin." 1657       the year may be a separate argument
  feastdate "Fer. 2. Pent." 1724       Whit Monday
  feastdate --easter 1744              Easter Sunday of that year
  feastdate --gregorian "Dom. 1. Adv. 1650"   a Catholic parish

default calendar: Julian to 1699, the Protestant Improved Calendar from 1700.
a year inside the text is read only from 1500 to 1899; give any other year
(1 to 9999) as the last argument."""

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
    p.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    p.set_defaults(cal='P')
    return p


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    p = build_parser()
    args = p.parse_args(argv)
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
    # three digits, so a three-digit-or-longer last word is always a year.
    if len(words) > 1 and re.fullmatch(r'\d{3,}', words[-1].strip()):
        try:
            year = year_arg(words.pop())
        except argparse.ArgumentTypeError as e:
            p.error(str(e))
    text = ' '.join(words)
    try:
        o, what = resolve(text, year, args.cal)
    except FeastError as e:
        print('feastdate: %s' % e, file=sys.stderr)
        return 2
    # The year the text already carries (resolve() refused any other) is not repeated.
    if year is None or re.search(r'(?<!\d)%d(?!\d)' % year, text):
        label = text
    else:
        label = '%s %d' % (text, year)
    print('%s = %s   [%s]' % (label, show(o, args.cal), what))
    return 0


if __name__ == '__main__':
    sys.exit(main())
