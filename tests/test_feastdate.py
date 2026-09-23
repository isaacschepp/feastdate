import re

import pytest

from feastdate import (FE, SWITCH, FeastError, cal_of_year, easter, feast_date, fmt, j2o,
                       resolve, show, to_ord)
from feastdate.cli import main


# Dates settled from the registers themselves.
@pytest.mark.parametrize('text, year, cal, want', [
    ('Dom. Judica.', 1658, 'P', 'Sun 28 Mar 1658 (Julian)'),
    ('Dom. 4. Trinit. 1647', None, 'P', 'Sun 11 Jul 1647 (Julian)'),
    ('Dom. 9. Trin.', 1657, 'P', 'Sun 26 Jul 1657 (Julian)'),
    ('Dom. Palm. 1656', None, 'P', 'Sun 30 Mar 1656 (Julian)'),
    ('Die Viridium', 1724, 'P', 'Thu 6 Apr 1724 (Gregorian)'),   # Protestant Easter 1724
    ('Pasch.', 1744, 'P', 'Sun 29 Mar 1744 (Gregorian)'),        # Protestant Easter 1744
    ('Pasch.', 1744, 'G', 'Sun 5 Apr 1744 (Gregorian)'),         # Gregorian Easter 1744
    ('Dom. 1. Adv.', 1656, 'P', 'Sun 30 Nov 1656 (Julian)'),
    # 6 Jan 1656 (Julian) was itself a Sunday, so the first Sunday AFTER Epiphany is 13 Jan.
    ('Dom. III. Epiph.', 1656, 'P', 'Sun 27 Jan 1656 (Julian)'),
    ('Festo Purif.', 1656, 'P', 'Sat 2 Feb 1656 (Julian)'),
])
def test_anchor(text, year, cal, want):
    assert feast_date(text, year, cal) == want


# Spellings resolve to the same day as the canonical name.
SAME = [('Dom. Reminisc:', 'Reminiscere'), ('Dom. Lætare.', 'Laetare'),
        ('Dom. Quasim.', 'Quasimodogeniti'), ('Dom. Quas.', 'Quasimodogeniti'),
        ('Dom. Miser. Dni.', 'Misericordias Domini'), ('Dom. Voc. jucund.', 'Rogate'),
        ('Dom. Rogation.', 'Rogate'), ('Dom. Estomihi.', 'Estomihi'),
        ('Dom. Quinq.', 'Estomihi'), ('Dom. Palmar.', 'Palm Sunday'),
        ('Dom. Cantat.', 'Cantate'), ('Dom. Jubil.', 'Jubilate'),
        ('Dom. Invoc.', 'Invocavit'), ('Dom. Septuag:', 'Septuagesima'),
        ('Dom. Sexag.', 'Sexagesima'), ('Dom. Oculi.', 'Oculi'), ('Exaudi', 'Exaudi'),
        ('Whit Sunday', 'Pentecost'), ('Ascension', 'Ascension'),
        ('Fer. 2. Pent.', 'Whit Monday'), ('Feria 2da Paschat.', 'Easter Monday'),
        ('Fer. 3. Pasch.', 'Easter Tuesday'), ('Dom. Trinit.', 'Trinity'),
        ('Fest. Trinit.', 'Trinity')]
YEARS = (1647, 1656, 1690, 1712, 1724)


@pytest.mark.parametrize('year', YEARS)
@pytest.mark.parametrize('spelled, name', SAME)
def test_spellings(spelled, name, year):
    assert resolve(spelled, year)[0] == easter(year) + FE[name]


@pytest.mark.parametrize('year', YEARS)
def test_trinity_ordinals(year):
    e = easter(year)
    assert resolve('Dom XXIII post Trin.', year)[0] == e + 56 + 161
    assert resolve('9th Sunday after Trinity', year)[0] == e + 56 + 63


@pytest.mark.parametrize('cal', ['P', 'G', 'J'])
def test_every_sunday_is_a_sunday(cal):
    """Across both calendars and the 1700 switch."""
    for yr in range(1600, 1800):
        for name in ('Dom. 1. Adv.', 'Dom. 4. Adv.', 'Dom. 5. p. Epiph.', 'Dom. Palm.',
                     'Dom. 27. Trin.'):
            assert resolve(name, yr, cal)[0] % 7 == 6, (name, yr, cal)


@pytest.mark.parametrize('year', [1650, 1699, 1700, 1750])
def test_advent_1_window(year):
    """Advent 1 falls between 27 Nov and 3 Dec."""
    a1 = show(resolve('Dom. 1. Adv.', year)[0], 'P')
    assert re.search(r' (2[7-9]|30) Nov | [1-3] Dec ', a1)


def test_the_1700_switch():
    assert show(SWITCH - 1, 'P') == 'Sun 18 Feb 1700 (Julian)'
    assert show(SWITCH, 'P') == 'Mon 1 Mar 1700 (Gregorian)'


@pytest.mark.parametrize('bad, why', [
    ('Dom. Palm.', 'no year'),
    ('Dom XV post 1656', 'post'),
    ('Dom. 1656', 'no feast'),
    ('Dom. 5. Adv. 1656', 'Advent'),
])
def test_refused(bad, why):
    with pytest.raises(FeastError) as e:
        resolve(bad)
    assert why.split()[-1] in str(e.value)


@pytest.mark.parametrize('text, name', [
    ('Ostermontag', 'Easter Monday'), ('Oster Montag', 'Easter Monday'),
    ('Osterdienstag', 'Easter Tuesday'), ('Pfingstmontag', 'Whit Monday'),
    ('Pfingstdienstag', 'Whit Tuesday'), ('Pfingst Dienstag', 'Whit Tuesday'),
])
def test_german_weekday_compounds(text, name):
    """The weekday inside a compound word must count, not fall back to the Sunday."""
    for yr in YEARS:
        assert resolve(text, yr)[0] == easter(yr) + FE[name]


def test_two_years_refused():
    with pytest.raises(FeastError):
        resolve('Dom. Palm. 1656', 1657)


def test_cli_feast(capsys):
    assert main(['Dom. Palm. 1656']) == 0
    assert capsys.readouterr().out == 'Dom. Palm. 1656 = Sun 30 Mar 1656 (Julian)   [palm]\n'


def test_cli_year_as_separate_argument(capsys):
    assert main(['Dom. 9. Trin.', '1657']) == 0
    assert 'Sun 26 Jul 1657 (Julian)' in capsys.readouterr().out


def test_cli_easter(capsys):
    assert main(['--easter', '1744']) == 0
    assert capsys.readouterr().out == 'Easter 1744 = Sun 29 Mar 1744 (Gregorian)\n'
    assert main(['--gregorian', '--easter', '1744']) == 0
    assert capsys.readouterr().out == 'Easter 1744 = Sun 5 Apr 1744 (Gregorian)\n'


def test_cli_error(capsys):
    assert main(['Dom. Palm.']) == 2
    assert 'no year' in capsys.readouterr().err


def test_cli_unknown_flag():
    with pytest.raises(SystemExit) as e:
        main(['--gregorain', 'Dom. Palm. 1656'])
    assert e.value.code == 2


@pytest.mark.parametrize('text, want', [
    # 1 Jan to 18 Feb 1700 were still Julian in the Protestant estates.
    ('Circumcis. 1700', 'Mon 1 Jan 1700 (Julian)'),
    ('Epiph. 1700', 'Sat 6 Jan 1700 (Julian)'),
    ('Dom. 1. p. Epiph. 1700', 'Sun 7 Jan 1700 (Julian)'),
    ('Purif. 1700', 'Fri 2 Feb 1700 (Julian)'),
    # From 1 Mar 1700 the Improved Calendar.
    ('Annunc. 1700', 'Thu 25 Mar 1700 (Gregorian)'),
    ('Nativ. 1700', 'Sat 25 Dec 1700 (Gregorian)'),
])
def test_fixed_feasts_in_1700(text, want):
    assert feast_date(text) == want


def test_fmt_across_the_switch():
    assert fmt(SWITCH - 1) == '18 Feb 1700'
    assert fmt(SWITCH) == '1 Mar 1700'
    assert fmt(j2o(1700, 1, 6)) == '6 Jan 1700'


def test_cli_separate_year_outside_the_text_window(capsys):
    assert main(['Dom. 9. Trin.', '1950']) == 0
    assert capsys.readouterr().out.startswith('Dom. 9. Trin. 1950 = Sun ')
    assert main(['Dom. 9. Trin. 1657', '1657']) == 0
    assert main(['Dom. 9. Trin. 1657', '1658']) == 2
    assert 'two years' in capsys.readouterr().err


@pytest.mark.parametrize('argv', [['--easter', '-5'], ['--easter', '0'], ['--easter', '10000'],
                                  ['Dom. Palm.', '10000']])
def test_cli_year_range_is_the_same_on_every_route(argv):
    with pytest.raises(SystemExit) as e:
        main(argv)
    assert e.value.code == 2


@pytest.mark.parametrize('d', range(19, 30))
def test_to_ord_rejects_the_dropped_days_of_1700(d):
    # 18 Feb 1700 (Julian) was followed by 1 Mar 1700 in the Protestant estates.
    with pytest.raises(FeastError, match='does not exist'):
        to_ord(1700, 2, d, 'P')


def test_to_ord_is_monotonic_across_the_switch():
    assert to_ord(1700, 2, 18, 'P') + 1 == to_ord(1700, 3, 1, 'P') == SWITCH
    assert show(to_ord(1700, 2, 18, 'P'), 'P') == 'Sun 18 Feb 1700 (Julian)'
    assert show(to_ord(1700, 3, 1, 'P'), 'P') == 'Mon 1 Mar 1700 (Gregorian)'


@pytest.mark.parametrize('y, m, d, cal', [
    (1656, 2, 30, 'P'), (1800, 2, 29, 'G'), (1800, 2, 29, 'P'), (1656, 13, 1, 'J'),
])
def test_to_ord_rejects_days_that_do_not_exist(y, m, d, cal):
    with pytest.raises(FeastError, match='does not exist'):
        to_ord(y, m, d, cal)


def test_to_ord_accepts_julian_leap_days():
    assert show(to_ord(1600, 2, 29, 'P'), 'P') == 'Fri 29 Feb 1600 (Julian)'
    assert show(to_ord(1700, 2, 29, 'J'), 'J') == 'Thu 29 Feb 1700 (Julian)'


def test_cal_of_year_answers_for_the_day():
    assert cal_of_year(1700, 'P', 1, 6) == 'J'
    assert cal_of_year(1700, 'P', 2, 18) == 'J'
    assert cal_of_year(1700, 'P', 3, 1) == 'G'
    assert cal_of_year(1700, 'P') == 'G'
    assert cal_of_year(1699, 'P') == 'J'
    assert cal_of_year(1700, 'G', 1, 6) == 'G'
