"""Command line: ``feastdate "Dom. Palm. 1656"`` -> ``Sun 30 Mar 1656 (Julian)``."""
import argparse
import sys

from . import __version__
from .core import FeastError, easter_of, resolve, show

EPILOG = """examples:
  feastdate "Dom. Palm. 1656"          Sun 30 Mar 1656 (Julian)
  feastdate "Dom. 9. Trin." 1657       the year may be a separate argument
  feastdate "Fer. 2. Pent." 1724       Whit Monday
  feastdate --easter 1744              Easter Sunday of that year
  feastdate --gregorian "Dom. 1. Adv. 1650"   a Catholic parish

default calendar: Julian to 1699, the Protestant Improved Calendar from 1700."""


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
    p.add_argument('--easter', metavar='YEAR', type=int,
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
    text = ' '.join(args.text)
    try:
        o, what = resolve(text, None, args.cal)
    except FeastError as e:
        print('feastdate: %s' % e, file=sys.stderr)
        return 2
    print('%s = %s   [%s]' % (text, show(o, args.cal), what))
    return 0


if __name__ == '__main__':
    sys.exit(main())
