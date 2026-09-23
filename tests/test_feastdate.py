import io
import json
import re

import pytest

from feastdate import (FE, SWITCH, FeastError, cal_of_year, easter, easter_of, feast_date, fmt,
                       j2o, name_of, resolve, show, to_ord, week_of, ymd)
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
        for name in ('Dom. 1. Adv.', 'Dom. 4. Adv.', 'Dom. 1. p. Epiph.', 'Dom. Palm.',
                     'Dom. 22. Trin.'):
            assert resolve(name, yr, cal)[0] % 7 == 6, (name, yr, cal)


def _sundays(name, yr, cal):
    """The ordinals ``name`` (with ``{}`` for the number) resolves to, for n = 0 to 39."""
    out = []
    for n in range(40):
        try:
            out.append(resolve(name.format(n), yr, cal)[0])
        except FeastError:
            pass
    return out


@pytest.mark.parametrize('cal', ['P', 'G', 'J'])
def test_numbered_sundays_end_where_the_next_season_begins(cal):
    """Every year has 22 to 27 Sundays after Trinity, the last a week before Advent 1, and
    1 to 6 after Epiphany, the last a week before Septuagesima. No other number resolves."""
    for yr in range(1600, 1800):
        trin = _sundays('Dom. {}. Trin.', yr, cal)
        assert 22 <= len(trin) <= 27, (yr, cal, len(trin))
        assert trin[-1] + 7 == resolve('Dom. 1. Adv.', yr, cal)[0], (yr, cal)
        epi = _sundays('Dom. {}. p. Epiph.', yr, cal)
        assert 1 <= len(epi) <= 6, (yr, cal, len(epi))
        assert epi[-1] + 7 == resolve('Septuag.', yr, cal)[0], (yr, cal)
        assert all(o % 7 == 6 for o in trin + epi), (yr, cal)


@pytest.mark.parametrize('year', [1650, 1699, 1700, 1750])
def test_advent_1_window(year):
    """Advent 1 falls between 27 Nov and 3 Dec."""
    a1 = show(resolve('Dom. 1. Adv.', year)[0], 'P')
    assert re.search(r' (2[7-9]|30) Nov | [1-3] Dec ', a1)


def test_the_1700_switch():
    assert show(SWITCH - 1, 'P') == 'Sun 18 Feb 1700 (Julian)'
    assert show(SWITCH, 'P') == 'Mon 1 Mar 1700 (Gregorian)'


@pytest.mark.parametrize('bad, why', [
    ('Dom. Palm.', '^no year: '),
    ('Dom XV post 1656', '^"post" with no feast named'),
    ('Dom. 1656', '^no feast recognised in '),
    ('Dom. 5. Adv. 1656', '^Advent needs its Sunday'),
    # A misread numeral must not answer a Sunday of the next season.
    ('Dom. 28. Trin. 1680', '^there were 24 Sundays after Trinity in 1680, not 28'),
    ('Dom. 25. Trin. 1680', '^there were 24 Sundays after Trinity in 1680, not 25'),
    ('Dom. 0. Trin. 1680', '^there were 24 Sundays after Trinity in 1680, not 0'),
    ('Dom. 7. p. Epiph. 1680', '^there were 4 Sundays after Epiphany in 1680, not 7'),
    ('Dom. 5. p. Epiph. 1680', '^there were 4 Sundays after Epiphany in 1680, not 5'),
    ('Dom. 0. p. Epiph. 1680', '^there were 4 Sundays after Epiphany in 1680, not 0'),
    ('Fer. 9. Pasch. 1680', '^feria counts the days of the week, 1 to 7, not 9'),
    ('Fer. 0. Pent. 1680', '^feria counts the days of the week, 1 to 7, not 0'),
    ('Fer. 8. Trin. 1680', '^feria counts the days of the week, 1 to 7, not 8'),
    # With a weekday feast the feria names the feast's own weekday, not an offset (#3).
    ('Fer. 2. Ascens. 1680', '^feria 2 does not fall on ascens, a Thursday'),
    ('Feria 2 in Parasceve 1680', '^feria 2 does not fall on parasceve, a Friday'),
    ('Feria 6 in Coena Domini 1680', '^feria 6 does not fall on coena, a Thursday'),
])
def test_refused(bad, why):
    # Anchored on each branch's own wording: the catch-all quotes the input back, so a
    # bare word from the input ("post") would match it and pass with the branch gone.
    with pytest.raises(FeastError, match=why):
        resolve(bad)


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


@pytest.mark.parametrize('short', ['5', '30', '0'])
def test_cli_short_separate_number_is_an_ordinal(short, capsys):
    """A separate year needs three digits; a shorter last word stays an ordinal, and the
    error says so rather than leave "no year" unexplained."""
    assert main(['Dom. Palm.', short]) == 2
    err = capsys.readouterr().err
    assert err.startswith('feastdate: no year')
    assert 'three digits or more, 100 to 9999; %s is read as an ordinal' % short in err


def test_cli_three_digit_separate_year(capsys):
    assert main(['Dom. Palm.', '500']) == 0
    assert capsys.readouterr().out == 'Dom. Palm. 500 = Sun 26 Mar 500 (Julian)   [palm]\n'


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
    assert capsys.readouterr().out.startswith('Dom. 9. Trin. 1657 = Sun ')
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


# The day of a German feast, counted: #353. Each row is dated in a register.
@pytest.mark.parametrize('text, want', [
    # Rompf-54: "d. 3.t April 1747, war der 2t Ostertag"
    ('der 2t Ostertag 1747', 'Mon 3 Apr 1747 (Gregorian)'),
    ('2. Ostertag 1747', 'Mon 3 Apr 1747 (Gregorian)'),
    ('der 2te Ostertag 1747', 'Mon 3 Apr 1747 (Gregorian)'),
    ('2ter Ostertag 1747', 'Mon 3 Apr 1747 (Gregorian)'),
    ('zweiter Ostertag 1747', 'Mon 3 Apr 1747 (Gregorian)'),
    ('2. Oster Tag 1747', 'Mon 3 Apr 1747 (Gregorian)'),
    ('2. Osterfeiertag 1747', 'Mon 3 Apr 1747 (Gregorian)'),
    # Langsdorff-15: "Den 19. t. April 1740, als d. 3ten Ostertag"
    ('3. Ostertag 1740', 'Tue 19 Apr 1740 (Gregorian)'),
    ('d. 3ten Ostertag 1740', 'Tue 19 Apr 1740 (Gregorian)'),
    # Pohl-Göns KB1 p. 67: "Den 11. April war der dritte Ostertag"
    ('dritter Ostertag 1699', 'Tue 11 Apr 1699 (Julian)'),
    ('der dritte Ostertag 1699', 'Tue 11 Apr 1699 (Julian)'),
    # KB1 p. 217: "d 1 April, war der letzte Ostertag"
    ('letzter Ostertag 1766', 'Tue 1 Apr 1766 (Gregorian)'),
    ('der letzte Ostertag 1766', 'Tue 1 Apr 1766 (Gregorian)'),
    ('erster Ostertag 1747', 'Sun 2 Apr 1747 (Gregorian)'),
    ('Ostertag 1747', 'Sun 2 Apr 1747 (Gregorian)'),
    ('2. Pfingsttag 1740', 'Mon 6 Jun 1740 (Gregorian)'),
    ('3. Pfingsttag 1740', 'Tue 7 Jun 1740 (Gregorian)'),
    ('zweiter Pfingstfeiertag 1740', 'Mon 6 Jun 1740 (Gregorian)'),
    ('2. Weihnachtstag 1740', 'Mon 26 Dec 1740 (Gregorian)'),
    ('3. Weihnachtstag 1740', 'Tue 27 Dec 1740 (Gregorian)'),
    ('2. Christtag 1740', 'Mon 26 Dec 1740 (Gregorian)'),
    ('Feria secunda Paschatos 1740', 'Mon 18 Apr 1740 (Gregorian)'),
    ('Fer. tertia Pent. 1740', 'Tue 7 Jun 1740 (Gregorian)'),
    # A weekday feast: the feria is the feast's own weekday and adds nothing (#3).
    ('Feria 6 in Parasceve 1680', 'Fri 9 Apr 1680 (Julian)'),
    ('Feria sexta in Parasceve 1680', 'Fri 9 Apr 1680 (Julian)'),
    ('Feria V in Coena Domini 1680', 'Thu 8 Apr 1680 (Julian)'),
    ('Feria quinta in Coena Domini 1680', 'Thu 8 Apr 1680 (Julian)'),
    ('Fer. 5. Ascens. 1680', 'Thu 20 May 1680 (Julian)'),
])
def test_day_of_the_feast(text, want):
    assert feast_date(text) == want


# Nothing in the text may be dropped: a word or number the parser cannot account for is
# refused, never skipped. Each of these used to answer a plausible wrong date.
@pytest.mark.parametrize('bad, why', [
    ('2. Ostern 1747', 'not used'),                 # the Sunday, with the 2 dropped
    ('2. Pfingsten 1740', 'not used'),
    ('2. Weihnachten 1740', 'not used'),
    ('2. Palm. 1740', 'not used'),
    ('4. Ostertag 1740', 'at most'),
    ('2. Palmtag 1740', 'not used'),
    ('2. Johannistag 1740', 'not used'),
    ('letzter Palm. 1740', 'letzter'),
    ('2. Ostermontag 1740', 'weekday'),
    ('Fer. 2. Ostermontag 1740', 'weekday'),
    ('Fer. Pasch. 1740', 'feria needs'),
    ('Fer. 2. Nativ. 1740', 'feria'),
    ('Dom. Palm. Oculi 1740', 'more than one feast'),
    ('2. 3. Ostertag 1740', 'more than one ordinal'),
    ('Grüner Donnerstag 1740', 'no feast'),
    ('Dom. Palm. Jahr 1740', 'unrecognised'),
    ('Good Sunday 1740', 'is a Fri'),                 # a weekday that disagrees
    ('Dominica Viridium 1740', 'is a Thu'),
    # The register's whole sentence carries a calendar date too: refuse, do not guess.
    ('d. 3.t April 1747, war der 2t Ostertag', 'more than one ordinal'),
])
def test_unaccounted_input_is_refused(bad, why):
    with pytest.raises(FeastError) as e:
        resolve(bad)
    assert why.lower() in str(e.value).lower()


@pytest.mark.parametrize('text', [
    'Dominica Palmarum 1740', 'Festo S. Michaelis 1740', 'Weißer Sonntag 1740',
    'Coena Domini 1740', 'Dom. Esto mihi 1740', 'Mariae Verk. 1740', 'Mariä Verkündigung 1740',
    'Joh. Bapt. 1740', 'Fest. Ascens. Domini 1740', 'Christi Himmelfahrt 1740',
    'Palmsonntag 1740', 'Good Friday 1740', 'Easter Day 1740', 'Dom. Quasimodo geniti 1740',
])
def test_connecting_words_still_accepted(text):
    resolve(text)


def test_day_of_the_feast_cli(capsys):
    assert main(['der 2t Ostertag 1747']) == 0
    assert 'Mon 3 Apr 1747 (Gregorian)' in capsys.readouterr().out
    assert main(['2. Ostern 1747']) == 2
    assert 'not used' in capsys.readouterr().err


# Saints' days (#4). Each spelling lands on its (month, day), in a common year.
@pytest.mark.parametrize('text, md', [
    ('Pauli Bekehrung', (1, 25)), ('Bekehrung Pauli', (1, 25)), ('Conversio S. Pauli', (1, 25)),
    ('Matthiae Apost.', (2, 24)), ('Matthias', (2, 24)), ('Mathiae', (2, 24)),
    ('Gregorii', (3, 12)), ('Georgii', (4, 23)), ('Georgi', (4, 23)),
    ('Philippi Jacobi', (5, 1)), ('Philippi et Jacobi', (5, 1)), ('Phil. Jac.', (5, 1)),
    ('Walpurgis', (5, 1)),
    ('Kreuzerfindung', (5, 3)), ('Inventio S. Crucis', (5, 3)),
    ('Petri et Pauli', (6, 29)), ('Petri Pauli', (6, 29)), ('Peter und Paul', (6, 29)),
    ('Visitationis Mariae', (7, 2)), ('Mariä Heimsuchung', (7, 2)),
    ('Mariae Magdalenae', (7, 22)), ('Jacobi Apost.', (7, 25)), ('Laurentii Martyr.', (8, 10)),
    ('Assumptionis Mariae', (8, 15)), ('Mariä Himmelfahrt', (8, 15)),
    ('Himmelfahrt Mariae', (8, 15)),
    ('Bartholomaei', (8, 24)), ('Bartholomäi', (8, 24)),
    ('Nativ. Mariae', (9, 8)), ('Mariae Geburt', (9, 8)),
    ('Kreuzerhöhung', (9, 14)), ('Exaltatio Crucis', (9, 14)),
    ('Matthaei Apost. et Evang.', (9, 21)), ('Matthäi', (9, 21)), ('Matthäus', (9, 21)),
    ('Michaelis Archangeli', (9, 29)), ('Galli', (10, 16)),
    ('Simonis et Judae', (10, 28)), ('Simon Juda', (10, 28)),
    ('Omnium Sanctorum', (11, 1)), ('Allerheiligen', (11, 1)),
    ('Omnium Animarum', (11, 2)), ('Allerseelen', (11, 2)),
    ('Elisabethae', (11, 19)), ('Andreae Apost.', (11, 30)), ('Thomae Apost.', (12, 21)),
    ('Johannis Evang.', (12, 27)), ('Joh. Evangelistae', (12, 27)),
    ('Innocentium', (12, 28)), ('Unschuldige Kindlein', (12, 28)),
])
@pytest.mark.parametrize('year, cal', [(1681, 'P'), (1735, 'P'), (1681, 'G')])
def test_saints_days(text, md, year, cal):
    assert resolve(text, year, cal)[0] == to_ord(year, *md, cal)


@pytest.mark.parametrize('text, want', [
    # The St Bartholomew's Day massacre began on Sunday 24 Aug 1572.
    ('Bartholomaei 1572', 'Sun 24 Aug 1572 (Julian)'),
    # Luther's theses, 31 Oct 1517, were the eve of All Saints: a Saturday.
    ('Omnium Sanctorum 1517', 'Sun 1 Nov 1517 (Julian)'),
])
def test_saints_days_anchor(text, want):
    assert feast_date(text) == want


# For each pair the two-word name wins, and the one word alone keeps its old meaning.
@pytest.mark.parametrize('two, one', [
    (('Nativ. Mariae', (9, 8)), ('Nativ.', (12, 25))),
    (('Mariae Himmelfahrt', (8, 15)), ('Christi Himmelfahrt', None)),
    (('Johannis Evang.', (12, 27)), ('Johannis', (6, 24))),
    (('Philippi Jacobi', (5, 1)), ('Jacobi', (7, 25))),
    (('Matthiae', (2, 24)), ('Matthaei', (9, 21))),
])
def test_collisions(two, one):
    yr = 1681
    assert resolve(two[0], yr)[0] == to_ord(yr, *two[1], 'P')
    want = easter(yr) + FE['Ascension'] if one[1] is None else to_ord(yr, *one[1], 'P')
    assert resolve(one[0], yr)[0] == want


# Matthias is 25 Feb in a leap year, by the leap year of the calendar in force that day.
@pytest.mark.parametrize('text, cal, want', [
    ('Matthiae 1680', 'P', 'Wed 25 Feb 1680 (Julian)'),
    ('Matthiae 1681', 'P', 'Thu 24 Feb 1681 (Julian)'),
    ('Matthiae 1704', 'P', 'Mon 25 Feb 1704 (Gregorian)'),
    ('Matthiae 1800', 'P', 'Mon 24 Feb 1800 (Gregorian)'),   # no Gregorian leap day
    ('Matthiae 1800', 'J', 'Sat 25 Feb 1800 (Julian)'),      # a Julian leap year
    ('Matthiae 1600', 'G', 'Fri 25 Feb 1600 (Gregorian)'),
])
def test_matthias_leap_day(text, cal, want):
    assert feast_date(text, cal=cal) == want


def test_matthias_leap_day_is_labelled():
    assert resolve('Matthiae 1680')[1] == 'fixed feast 25 Feb, leap year'
    assert resolve('Matthiae 1681')[1] == 'fixed feast 24 Feb'


def test_matthias_1700_did_not_happen_in_the_protestant_estates():
    # 18 Feb 1700 (Julian) was followed by 1 Mar 1700.
    with pytest.raises(FeastError, match='does not exist in the Protestant calendar'):
        resolve('Matthiae 1700')


@pytest.mark.parametrize('bad, why', [
    ('Pauli 1680', 'no feast'),                     # Paul alone is no feast day
    ('Petri 1680', 'no feast'),
    ('Mariae 1680', 'no feast'),
    ('Johannis Jacobi 1680', 'more than one feast'),
    ('Petri Jahr Pauli 1680', 'unrecognised'),      # only connecting words may sit between
    ('2. Bartholomaei 1680', 'not used'),
])
def test_saints_days_refused(bad, why):
    with pytest.raises(FeastError) as e:
        resolve(bad)
    assert why.lower() in str(e.value).lower()


# Ash Wednesday, Holy Saturday, Shrove Tuesday and Corpus Christi, in days from Easter.
@pytest.mark.parametrize('text, off', [
    ('Aschermittwoch', -46), ('Dies Cinerum', -46), ('Feria IV Cinerum', -46),
    ('Ash Wednesday', -46),
    ('Karsamstag', -1), ('Charsamstag', -1), ('Karsonnabend', -1), ('Ostersamstag', -1),
    ('Ostersonnabend', -1), ('Oster Samstag', -1), ('Sabbatho Sancto', -1),
    ('Sabbato sancto', -1), ('Holy Saturday', -1),
    ('Fronleichnam', 60), ('Festo Corporis Christi', 60), ('Corpus Christi', 60),
    ('Feria V Corporis Christi', 60),
    ('Fastnachtsdienstag', -47), ('Fastnacht Dienstag', -47),
    ('Fastnacht', -49),             # Estomihi, as before: the weekday is what moves it
])
@pytest.mark.parametrize('year, cal', [(1680, 'P'), (1724, 'P'), (1735, 'G')])
def test_lent_and_corpus_christi(text, off, year, cal):
    assert resolve(text, year, cal)[0] == easter_of(year, cal) + off


@pytest.mark.parametrize('text, want', [
    ('Aschermittwoch 1680', 'Wed 25 Feb 1680 (Julian)'),     # 1680 is a leap year
    ('Sabbatho Sancto 1680', 'Sat 10 Apr 1680 (Julian)'),
    ('Fronleichnam 1680', 'Thu 10 Jun 1680 (Julian)'),
    ('Fastnachtsdienstag 1680', 'Tue 24 Feb 1680 (Julian)'),
    ('Fronleichnam 1724', 'Thu 8 Jun 1724 (Gregorian)'),      # the Protestant Easter of 1724
])
def test_lent_and_corpus_christi_anchor(text, want):
    assert feast_date(text) == want


@pytest.mark.parametrize('bad, why', [
    ('Ostersamstag 1680', None),                    # was Easter Sunday: must be the Saturday
    ('Sabbatho 1680', 'no feast'),                  # half a two-word name
    ('Corporis 1680', 'no feast'),
    ('Fer. 3 Cinerum 1680', 'does not fall'),       # Ash Wednesday is feria 4
    ('Dominica Cinerum 1680', 'wed'),               # a weekday word is a check
    ('Karfreitag Montag 1680', 'from a sunday'),    # used to answer a Saturday
    ('Aschermittwoch Dienstag 1680', 'from a sunday'),
    ('Buss und Bettag 1680', 'no feast'),           # varied by territory: refused on purpose
])
def test_lent_and_corpus_christi_refused(bad, why):
    if why is None:
        assert resolve(bad)[0] == easter(1680) - 1
        return
    with pytest.raises(FeastError) as e:
        resolve(bad)
    assert why in str(e.value).lower()


# A day counted from a feast (#6): the day before `nach` / `post` / `vor` / `ante`, the
# feast after it, and the count strictly after or before. Easter 1680 (Julian) is 11 Apr.
@pytest.mark.parametrize('text, want, what', [
    ('Freitag nach Jubilate 1680', 'Fri 7 May 1680 (Julian)', 'Friday after jubilate'),
    ('Friday after Jubilate 1680', 'Fri 7 May 1680 (Julian)', 'Friday after jubilate'),
    ('Mittwoch nach Oculi 1680', 'Wed 17 Mar 1680 (Julian)', 'Wednesday after oculi'),
    ('Montag nach Trinitatis 1680', 'Mon 7 Jun 1680 (Julian)', 'Monday after Trinity Sunday'),
    ('Sonnabend vor Palmarum 1680', 'Sat 3 Apr 1680 (Julian)', 'Saturday before palmarum'),
    ('Donnerstag vor Pfingsten 1680', 'Thu 27 May 1680 (Julian)', 'Thursday before pfingsten'),
    ('Feria 4 post Oculi 1680', 'Wed 17 Mar 1680 (Julian)', 'Wednesday after oculi'),
    ('Fer. 6 p. Reminisc. 1680', 'Fri 12 Mar 1680 (Julian)', 'Friday after reminisc'),
    ('Freitag nach Himmelfahrt 1680', 'Fri 21 May 1680 (Julian)', 'Friday after himmelfahrt'),
    # After the feast's own weekday word: the Friday after Easter Monday.
    ('Freitag nach Ostermontag 1680', 'Fri 16 Apr 1680 (Julian)', None),
    ('Mittwoch nach dem 3. Advent 1680', 'Wed 15 Dec 1680 (Julian)', None),
    ('Mittwoch nach dem 2. Pfingsttag 1680', 'Wed 2 Jun 1680 (Julian)', None),
    ('Dom. p. Nativ. 1680', 'Sun 26 Dec 1680 (Julian)', 'Sunday after fixed feast 25 Dec'),
    ('Sonntag nach Michaelis 1680', 'Sun 3 Oct 1680 (Julian)', None),
    ('Dom. post Circumcis. 1680', 'Sun 4 Jan 1680 (Julian)', None),
    ('Dom. post Martini 1680', 'Sun 14 Nov 1680 (Julian)', None),
    ('Dom. post Pascha 1680', 'Sun 18 Apr 1680 (Julian)', 'Sunday after pascha'),
    ('Dom. 1. post Pascha 1680', 'Sun 18 Apr 1680 (Julian)', '1. Sunday after pascha'),
    ('Dom. 2. p. Pasch. 1680', 'Sun 25 Apr 1680 (Julian)', '2. Sunday after pasch'),
    ('Dom. ante Circumcis. 1681', 'Sun 26 Dec 1680 (Julian)', None),
    # Strictly after: 29 Sep 1689 was itself a Sunday.
    ('Sonntag nach Michaelis 1689', 'Sun 6 Oct 1689 (Julian)', None),
    # The year is the feast's; the day counted from it can fall in the next.
    ('Dom. post Nativ. 1740', 'Sun 1 Jan 1741 (Gregorian)', None),
])
def test_day_counted_from_a_feast(text, want, what):
    assert feast_date(text) == want
    if what:
        assert resolve(text)[1] == what


@pytest.mark.parametrize('cal', ['P', 'G', 'J'])
def test_day_counted_from_a_feast_agrees_with_the_named_sundays(cal):
    for yr in range(1600, 1800):
        e = easter_of(yr, cal)
        assert resolve('Dom. post Pascha', yr, cal)[0] == e + 7
        for n in range(1, 7):
            assert resolve('Dom. %d. post Pascha' % n, yr, cal)[0] == e + 7 * n
        assert resolve('Dom. post Trin.', yr, cal)[0] == resolve('Dom. 1. Trin.', yr, cal)[0]
        assert resolve('Dom. post Epiph.', yr, cal)[0] == resolve('Dom. 1. p. Epiph.', yr, cal)[0]
        assert resolve('Dom. ante Nativ.', yr, cal)[0] == resolve('Dom. 4. Adv.', yr, cal)[0]
        assert resolve('Dom. post Pent.', yr, cal)[0] == resolve('Trinitatis', yr, cal)[0]
        for name in ('Martini', 'Michaelis', 'Johannis'):
            f = resolve(name, yr, cal)[0]
            after = resolve('Dom. post ' + name, yr, cal)[0]
            before = resolve('Dom. ante ' + name, yr, cal)[0]
            assert after % 7 == before % 7 == 6
            assert f < after <= f + 7 and f - 7 <= before < f


@pytest.mark.parametrize('bad, why', [
    ('post Martini 1680', 'needs the day it counts'),
    ('Jubilate nach Freitag 1680', 'the feast goes after'),
    ('Freitag Sonntag nach Jubilate 1680', 'two different days'),
    ('Feria 4 Freitag post Oculi 1680', 'two different days'),
    ('Freitag nach Dom. post Oculi 1680', 'more than one of'),
    ('2. Freitag nach Jubilate 1680', 'counts sundays, not fridays'),
    ('Dom. 2. post Martini 1680', 'only easter, pentecost, trinity and epiphany'),
    ('Dom. 2. ante Pascha 1680', 'only easter, pentecost, trinity and epiphany'),
    ('Dom. 2. ante Pent. 1680', 'only easter, pentecost, trinity and epiphany'),
    ('Dom. 7. post Pascha 1680', 'run 1 to 6, not 7'),
    ('Freitag nach Karfreitag Montag 1680', 'from a sunday'),
    ('Dom. post Jubilate Freitag 1680', 'is a sun'),   # a weekday after the feast checks it
    ('Freitag nach 1680', 'no feast'),
])
def test_day_counted_from_a_feast_refused(bad, why):
    with pytest.raises(FeastError) as e:
        resolve(bad)
    assert why in str(e.value).lower()


def test_weekday_without_nach_is_still_a_check():
    with pytest.raises(FeastError, match='is a Thu'):
        resolve('Dominica Viridium 1680')
    with pytest.raises(FeastError, match='is a Sun'):
        resolve('Freitag Jubilate 1680')


def test_day_counted_from_a_feast_cli(capsys):
    assert main(['Freitag nach Jubilate 1680']) == 0
    assert capsys.readouterr().out == ('Freitag nach Jubilate 1680 = Fri 7 May 1680 (Julian)'
                                       '   [Friday after jubilate]\n')


# Sundays numbered after Pentecost, the Catholic count, and the last Sunday after Trinity
# (#7). Pentecost 1680 (Julian) is 30 May; Advent 1 is 28 Nov.
@pytest.mark.parametrize('text, cal, want, what', [
    ('Dom. 5. post Pent. 1680', 'P', 'Sun 4 Jul 1680 (Julian)', '5. Sunday after pent'),
    ('Dominica 5. post Pentecosten 1680', 'P', 'Sun 4 Jul 1680 (Julian)', None),
    ('Dom. V. nach Pfingsten 1680', 'P', 'Sun 4 Jul 1680 (Julian)', None),
    ('Dom. 1. post Pent. 1680', 'P', 'Sun 6 Jun 1680 (Julian)', None),
    ('Dom. 25. post Pent. 1680', 'P', 'Sun 21 Nov 1680 (Julian)', None),
    ('Dom. 5. post Pent. 1680', 'G', 'Sun 14 Jul 1680 (Gregorian)', None),
    ('Dom. ult. p. Trin. 1680', 'P', 'Sun 21 Nov 1680 (Julian)', 'last Sunday after Trinity'),
    ('Dom. ult. Trin. 1680', 'P', 'Sun 21 Nov 1680 (Julian)', None),
    ('letzter Sonntag nach Trinitatis 1680', 'P', 'Sun 21 Nov 1680 (Julian)', None),
    ('Dom. ultima post Pent. 1680', 'P', 'Sun 21 Nov 1680 (Julian)',
     'last Sunday after Pentecost'),
    ('Dominica ultima post Pentecosten 1680', 'G', 'Sun 24 Nov 1680 (Gregorian)', None),
    # Prussia ordered it in 1816; the first fell on 24 Nov 1816.
    ('Totensonntag 1816', 'P', 'Sun 24 Nov 1816 (Gregorian)', None),
    ('Ewigkeitssonntag 1850', 'P', 'Sun 24 Nov 1850 (Gregorian)', None),
    ('Freitag nach Totensonntag 1850', 'P', 'Fri 29 Nov 1850 (Gregorian)', None),
])
def test_sundays_after_pentecost_and_the_last_sunday(text, cal, want, what):
    assert feast_date(text, cal=cal) == want
    if what:
        assert resolve(text, cal=cal)[1] == what


@pytest.mark.parametrize('cal', ['P', 'G', 'J'])
def test_pentecost_count_agrees_with_trinity_count(cal):
    """Dom. n+1 post Pent. is Dom. n. p. Trin., one more Sunday runs to Advent, and the last
    Sunday after Trinity or Pentecost is the last numbered one, a week before Advent 1."""
    for yr in range(1600, 1800):
        assert resolve('Dom. 1. post Pent.', yr, cal)[0] == resolve('Trinitatis', yr, cal)[0]
        trin = _sundays('Dom. {}. Trin.', yr, cal)
        pent = _sundays('Dom. {}. post Pent.', yr, cal)
        assert pent[1:] == trin, (yr, cal)
        assert 23 <= len(pent) <= 28, (yr, cal, len(pent))
        adv = resolve('Dom. 1. Adv.', yr, cal)[0]
        for name in ('Dom. ult. p. Trin.', 'Dom. ult. post Pent.',
                     'letzter Sonntag nach Trinitatis'):
            assert resolve(name, yr, cal)[0] == trin[-1] == adv - 7, (name, yr, cal)


def test_last_sunday_1680_is_the_24th():
    assert resolve('Dom. ult. p. Trin. 1680')[0] == resolve('Dom. 24. p. Trin. 1680')[0]


@pytest.mark.parametrize('bad, why', [
    ('Dom. 26. post Pent. 1680', 'there were 25 sundays after pentecost in 1680, not 26'),
    ('Dom. 0. post Pent. 1680', 'not 0'),
    ('Dom. ult. p. Epiph. 1680', 'trinity or pentecost only'),
    ('Dom. ult. p. Pascha 1680', 'trinity or pentecost only'),
    ('Dom. ult. ante Trin. 1680', 'last sunday after the feast'),
    ('ult. Freitag nach Trin. 1680', 'last sunday after the feast'),
    ('Dom. ult. 3. p. Trin. 1680', 'more than one ordinal'),
    ('Fer. 2. ult. p. Trin. 1680', 'more than one ordinal'),
    ('letzter Pfingsten 1680', 'names the last day of a feast'),
    ('Totensonntag 1815', 'ordered in prussia in 1816'),
    ('2. Totensonntag 1850', 'a number is not used'),
])
def test_sundays_after_pentecost_refused(bad, why):
    with pytest.raises(FeastError) as e:
        resolve(bad)
    assert why in str(e.value).lower()


# The reverse lookup (#8): a date -> the names the register gives it.
@pytest.mark.parametrize('ymd_, cal, want', [
    ((1657, 7, 26), 'P', [('Dom. 9. p. Trin.', '9th Sunday after Trinity')]),
    ((1724, 4, 6), 'P', [('Die Viridium', 'Maundy Thursday')]),       # Protestant Easter 1724
    ((1724, 4, 13), 'G', [('Die Viridium', 'Maundy Thursday')]),      # Gregorian Easter 1724
    ((1680, 4, 14), 'P', [('Feria 4 post Pascha', 'Wednesday after Easter')]),
    ((1656, 11, 30), 'P', [('Dom. 1. Adv.', '1st Sunday of Advent'), ('Andreae', 'St Andrew')]),
    ((1680, 11, 21), 'P', [('Dom. 24. p. Trin.', '24th Sunday after Trinity'),
                           ('Dom. ult. p. Trin.', 'last Sunday after Trinity')]),
    # Matthias moves to 25 Feb in a leap year, and 1680 is one.
    ((1680, 2, 25), 'P', [('Dies Cinerum', 'Ash Wednesday'), ('Matthiae', 'St Matthias')]),
    ((1680, 2, 24), 'P', [('Feria 3 post Estomihi', 'Shrove Tuesday, Tuesday after Estomihi')]),
    ((1656, 1, 13), 'P', [('Dom. 1. p. Epiph.', '1st Sunday after Epiphany')]),
    ((1680, 12, 26), 'P', [('Dom. p. Nativ.', 'Sunday after Christmas'),
                           ('Stephani', 'St Stephen, 2nd day of Christmas')]),
    ((1657, 7, 28), 'P', []),                   # a Tuesday in Trinity season: no name
    ((1680, 6, 20), 'G', [('Corpus Christi', 'Corpus Christi')]),
    # The same Thursday under 'P' is a feria: Corpus Christi is named only under 'G'.
    ((1680, 6, 10), 'P', [('Feria 5 post Trinitatis', 'Thursday after Trinity Sunday')]),
    ((1817, 11, 23), 'P', [('Dom. 25. p. Trin.', '25th Sunday after Trinity'),
                           ('Dom. ult. p. Trin.', 'last Sunday after Trinity'),
                           ('Totensonntag', 'Sunday of the Dead, the last before Advent')]),
])
def test_name_of(ymd_, cal, want):
    assert name_of(*ymd_, cal=cal) == want


def test_name_of_counts_after_pentecost_only_under_gregorian():
    assert name_of(1680, 7, 14, 'G') == [('Dom. 4. p. Trin.', '4th Sunday after Trinity'),
                                         ('Dom. 5. p. Pent.', '5th Sunday after Pentecost')]
    assert name_of(1680, 7, 4, 'P') == [('Dom. 4. p. Trin.', '4th Sunday after Trinity')]


def test_name_of_refuses_a_day_that_never_was():
    with pytest.raises(FeastError, match='does not exist'):
        name_of(1700, 2, 24)
    with pytest.raises(FeastError, match='does not exist'):
        name_of(1680, 2, 30)


def test_week_of():
    assert week_of(1657, 7, 28) == ('Tue', 'Dom. 9. p. Trin.')
    assert week_of(1657, 7, 26) == ('Sun', 'Dom. 9. p. Trin.')
    # 1 Mar 1700, the first day of the Improved Calendar, follows Invocavit, 18 Feb (Julian).
    assert week_of(1700, 3, 1) == ('Mon', 'Dom. Invocavit')
    assert name_of(1700, 3, 1) == [('Feria 2 post Invocavit', 'Monday after Invocavit')]
    assert name_of(1700, 2, 18) == [('Dom. Invocavit', 'Invocavit, 1st Sunday in Lent')]


@pytest.mark.parametrize('cal', ['P', 'G', 'J'])
def test_name_of_round_trips(cal):
    """Every name for every day of 1600 to 1799 resolves back to that day, every Sunday has
    a name, every day from Septuagesima to the week of Trinity has one, and so does every
    fixed feast. This ties the two directions together: drift in either fails here."""
    fixed = {'Circumcisio Domini', 'Epiphania Domini', 'Michaelis', 'Nativitas Christi',
             'Matthiae', 'Andreae', 'Johannis Baptistae'}
    for o in range(to_ord(1600, 1, 1, cal), to_ord(1800, 1, 1, cal)):
        y, m, d = ymd(o, cal)
        names = name_of(y, m, d, cal)
        assert len({n for n, _g in names}) == len(names), (y, m, d, cal)
        for name, _gloss in names:
            assert resolve(name, y, cal)[0] == o, (name, y, m, d, cal)
        if o % 7 == 6:
            assert names, ('nameless Sunday', y, m, d, cal)
        if -63 <= o - easter_of(y, cal) <= 62:
            assert names, ('nameless day in the Easter cycle', y, m, d, cal)
        fixed_here = fixed & {n for n, _g in names}
        for name in fixed_here:
            fixed_ok = True
            assert fixed_ok
    for y in range(1600, 1800):
        for name in fixed:
            try:
                o = resolve(name, y, cal)[0]
            except FeastError:
                continue                        # Matthias 1700 under 'P' never happened
            assert name in [n for n, _g in name_of(*ymd(o, cal), cal)], (name, y, cal)


@pytest.mark.parametrize('argv, out', [
    (['--date', '1657-07-26'], '26 Jul 1657 (Julian) = Sun   Dom. 9. p. Trin. (9th Sunday after Trinity)'),
    (['--date', '1724-04-06'], '6 Apr 1724 (Gregorian) = Thu   Die Viridium (Maundy Thursday)'),
    (['--date', '1680-04-14'], '14 Apr 1680 (Julian) = Wed   Feria 4 post Pascha (Wednesday after Easter)'),
    (['--date', '1657-07-28'], '28 Jul 1657 (Julian) = Tue   no name of its own: the week of Dom. 9. p. Trin.'),
    (['--gregorian', '--date', '1680-06-20'], '20 Jun 1680 (Gregorian) = Thu   Corpus Christi (Corpus Christi)'),
])
def test_date_cli(argv, out, capsys):
    assert main(argv) == 0
    assert capsys.readouterr().out.strip() == out


@pytest.mark.parametrize('argv, err', [
    (['--date', '1700-02-24'], 'does not exist in the Protestant calendar'),
    (['--date', '1680-13-01'], 'no month 13'),
])
def test_date_cli_refused(argv, err, capsys):
    assert main(argv) == 2
    assert err in capsys.readouterr().err


@pytest.mark.parametrize('argv', [['--date', '17x'], ['--date', '1680-04-14', 'Pascha'],
                                  ['--date', '1680-04-14', '--easter', '1680']])
def test_date_cli_usage_errors(argv):
    with pytest.raises(SystemExit) as e:
        main(argv)
    assert e.value.code == 2


# --- Machine-readable output and batch input (#9) ---------------------------------------


def test_iso_output(capsys):
    assert main(['--iso', 'Dom. Palm. 1656']) == 0
    assert capsys.readouterr().out == '1656-03-30 J\n'
    assert main(['--iso', 'Die Viridium 1724']) == 0
    assert capsys.readouterr().out == '1724-04-06 G\n'
    assert main(['--iso', '--easter', '1744']) == 0
    assert capsys.readouterr().out == '1744-03-29 G\n'


def test_json_round_trip_success(capsys):
    assert main(['--json', 'Dom. 9. Trin.', '1657']) == 0
    got = json.loads(capsys.readouterr().out)
    o, what = resolve('Dom. 9. Trin.', 1657)
    assert got == {'input': 'Dom. 9. Trin. 1657', 'date': '1657-07-26', 'calendar': 'Julian',
                   'weekday': 'Sun', 'jdn': o, 'parsed': what}
    assert show(got['jdn'], 'P') == 'Sun 26 Jul 1657 (Julian)'


def test_json_round_trip_refusal(capsys):
    assert main(['--json', 'Festo Blödsinn 1700']) == 2
    out = capsys.readouterr().out
    got = json.loads(out)
    assert set(got) == {'input', 'error'}
    assert got['input'] == 'Festo Blödsinn 1700' and 'no feast recognised' in got['error']
    assert 'Blödsinn' in out                    # not \u-escaped


def test_json_date(capsys):
    assert main(['--json', '--date', '1656-11-30']) == 0
    got = json.loads(capsys.readouterr().out)
    assert got['calendar'] == 'Julian' and got['weekday'] == 'Sun'
    assert [n['name'] for n in got['names']] == ['Dom. 1. Adv.', 'Andreae']


def test_iso_with_date_is_a_usage_error():
    with pytest.raises(SystemExit) as e:
        main(['--iso', '--date', '1656-11-30'])
    assert e.value.code == 2


@pytest.mark.parametrize('fmt', [[], ['--iso'], ['--json']])
def test_batch_keeps_going_past_a_refusal(fmt, monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin', io.StringIO('Dom. Palm. 1656\nDom. Palm.\nDom. 9. Trin.\t1950\n'))
    assert main(fmt + ['-']) == 2
    cap = capsys.readouterr()
    lines = cap.out.splitlines()
    assert len(lines) == 3
    assert 'line 2: no year' in cap.err
    if fmt == ['--json']:
        rows = [json.loads(ln) for ln in lines]
        assert [r.get('date') for r in rows] == ['1656-03-30', None, '1950-08-06']
        assert 'error' in rows[1]
    elif fmt == ['--iso']:
        assert lines == ['1656-03-30 J', 'error: no year: give one, e.g. "Dom. Palm. 1656"',
                         '1950-08-06 G']
    else:
        assert lines[0] == 'Dom. Palm. 1656 = Sun 30 Mar 1656 (Julian)   [palm]'
        assert lines[2].startswith('Dom. 9. Trin. 1950 = Sun 6 Aug 1950 (Gregorian)')


def test_batch_all_resolved_exits_0(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin', io.StringIO('Dom. Palm. 1656\r\nFesto Michaelis 1699\r\n'))
    assert main(['--iso']) == 0                 # no text, stdin not a terminal
    assert capsys.readouterr().out == '1656-03-30 J\n1699-09-29 J\n'


def test_batch_bad_year_column_and_empty_line(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin', io.StringIO('Dom. Palm.\t10000\n\n'))
    assert main(['--iso', '-']) == 2
    assert capsys.readouterr().out.splitlines() == [
        'error: year 10000 is outside 1 to 9999', 'error: empty line']


def test_no_text_on_a_terminal_still_prints_help(monkeypatch, capsys):
    class Tty(io.StringIO):
        def isatty(self):
            return True
    monkeypatch.setattr('sys.stdin', Tty(''))
    assert main([]) == 2
    assert 'usage:' in capsys.readouterr().out


# ---------------------------------------------------------------------------------------
# Calendar switches for other territories (--switch).

from feastdate import MON, SWITCHES, Switch, calendar_of, g2o, is_greg, o2j  # noqa: E402

# key: (last Julian day, first Gregorian day, the weekdays either side)
SWITCH_DAYS = {
    'de-protestant': ((1700, 2, 18), (1700, 3, 1), 'Sun', 'Mon'),
    'denmark-norway': ((1700, 2, 18), (1700, 3, 1), 'Sun', 'Mon'),
    'prussia-duchy': ((1610, 8, 22), (1610, 9, 2), 'Wed', 'Thu'),
    'sweden': ((1753, 2, 17), (1753, 3, 1), 'Wed', 'Thu'),
    'england': ((1752, 9, 2), (1752, 9, 14), 'Wed', 'Thu'),
    'british-colonies': ((1752, 9, 2), (1752, 9, 14), 'Wed', 'Thu'),
    'catholic': ((1582, 10, 4), (1582, 10, 15), 'Thu', 'Fri'),
}


def test_every_preset_is_tested():
    assert set(SWITCH_DAYS) == set(SWITCHES)


@pytest.mark.parametrize('key', sorted(SWITCH_DAYS))
def test_switch_day_before_and_after(key):
    (jy, jm, jd), (gy, gm, gd), wd_j, wd_g = SWITCH_DAYS[key]
    last, first = to_ord(jy, jm, jd, key), to_ord(gy, gm, gd, key)
    assert first == last + 1
    assert show(last, key) == '%s %d %s %d (Julian)' % (wd_j, jd, MON[jm - 1], jy)
    assert show(first, key) == '%s %d %s %d (Gregorian)' % (wd_g, gd, MON[gm - 1], gy)
    assert not is_greg(last, key) and is_greg(first, key)


@pytest.mark.parametrize('key', sorted(SWITCH_DAYS))
def test_switch_refuses_the_dropped_days(key):
    """Every day label between the last Julian and the first Gregorian day is refused."""
    (jy, jm, jd), first, _a, _b = SWITCH_DAYS[key]
    dropped = 0
    o = j2o(jy, jm, jd) + 1
    while o2j(o) < first:
        with pytest.raises(FeastError, match='does not exist in the .* calendar: .* was '
                                             'followed by'):
            to_ord(*o2j(o), key)
        dropped += 1
        o += 1
    assert dropped in (10, 11)


# A movable feast in the switch year, and Easter either side of it.
@pytest.mark.parametrize('text, key, want', [
    ('Pasch. 1700', 'denmark-norway', 'Sun 11 Apr 1700 (Gregorian)'),
    ('Pasch. 1724', 'denmark-norway', 'Sun 9 Apr 1724 (Gregorian)'),   # improved Easter
    ('Pasch. 1744', 'denmark-norway', 'Sun 29 Mar 1744 (Gregorian)'),
    ('Pasch. 1610', 'prussia-duchy', 'Sun 8 Apr 1610 (Julian)'),       # before Aug 1610
    ('Dom. 1. Adv. 1610', 'prussia-duchy', 'Sun 28 Nov 1610 (Gregorian)'),
    ('Pasch. 1611', 'prussia-duchy', 'Sun 3 Apr 1611 (Gregorian)'),
    ('Pasch. 1753', 'sweden', 'Sun 22 Apr 1753 (Gregorian)'),
    ('Pasch. 1744', 'sweden', 'Sun 18 Mar 1744 (Julian)'),             # = 29 Mar Gregorian
    ('Pasch. 1742', 'sweden', 'Sun 14 Mar 1742 (Julian)'),             # astronomical, from 1740
    ('Pasch. 1739', 'sweden', 'Sun 22 Apr 1739 (Julian)'),             # still the Julian rule
    ('Pasch. 1802', 'sweden', 'Sun 25 Apr 1802 (Gregorian)'),          # a week after Rome
    ('Pasch. 1805', 'sweden', 'Sun 21 Apr 1805 (Gregorian)'),
    ('Pasch. 1818', 'sweden', 'Sun 29 Mar 1818 (Gregorian)'),
    ('Pasch. 1825', 'sweden', 'Sun 3 Apr 1825 (Gregorian)'),           # should have been late
    ('Pasch. 1752', 'england', 'Sun 29 Mar 1752 (Julian)'),
    ('Michaelis 1752', 'england', 'Fri 29 Sep 1752 (Gregorian)'),
    ('Pasch. 1753', 'england', 'Sun 22 Apr 1753 (Gregorian)'),
    ('Pasch. 1582', 'catholic', 'Sun 15 Apr 1582 (Julian)'),
    ('Dom. 1. Adv. 1582', 'catholic', 'Sun 28 Nov 1582 (Gregorian)'),
    ('Pasch. 1583', 'catholic', 'Sun 10 Apr 1583 (Gregorian)'),
])
def test_switch_feasts(text, key, want):
    assert feast_date(text, cal=key) == want


def test_sundays_after_trinity_run_across_the_english_switch():
    # Trinity Sunday 1752 was Julian 24 May. The Sundays keep a seven-day step across the
    # eleven dropped days: the 14th is Julian 30 Aug, the 15th Gregorian 17 Sep.
    assert feast_date('Dom. Trin. 1752', cal='england') == 'Sun 24 May 1752 (Julian)'
    assert feast_date('Dom. 14. p. Trin. 1752', cal='england') == 'Sun 30 Aug 1752 (Julian)'
    assert feast_date('Dom. 15. p. Trin. 1752', cal='england') == 'Sun 17 Sep 1752 (Gregorian)'


def test_de_protestant_is_P():
    assert calendar_of('P') is SWITCHES['de-protestant']
    for yr in range(1600, 1800):
        assert easter_of(yr, 'de-protestant') == easter_of(yr, 'P') == easter(yr)
        assert to_ord(yr, 6, 1, 'de-protestant') == to_ord(yr, 6, 1, 'P')


def test_catholic_is_G_after_1582_and_J_before():
    for yr in range(1583, 1800):
        assert easter_of(yr, 'catholic') == easter_of(yr, 'G')
        assert name_of(yr, 6, 1, 'catholic') == name_of(yr, 6, 1, 'G')
    for yr in range(1500, 1582):
        assert easter_of(yr, 'catholic') == easter_of(yr, 'J')
        assert to_ord(yr, 6, 1, 'catholic') == to_ord(yr, 6, 1, 'J')


def test_england_is_gregorian_from_1753_and_julian_to_1752():
    for yr in range(1600, 1753):
        assert easter_of(yr, 'england') == easter_of(yr, 'J')
    for yr in range(1753, 1900):
        assert easter_of(yr, 'england') == easter_of(yr, 'G')


def test_prussia_refuses_the_disputed_easters():
    for yr in (1724, 1744):
        with pytest.raises(FeastError, match='not established whether Ducal Prussia'):
            easter_of(yr, 'prussia-duchy')
        with pytest.raises(FeastError, match='not established'):
            resolve('Pasch.', yr, 'prussia-duchy')
    # A fixed feast does not need Easter.
    assert feast_date('Michaelis 1724', cal='prussia-duchy') == 'Fri 29 Sep 1724 (Gregorian)'


def test_sweden_refuses_the_swedish_calendar_of_1700_to_1712():
    assert feast_date('Pasch. 1699', cal='sweden') == 'Sun 9 Apr 1699 (Julian)'
    assert to_ord(1700, 2, 28, 'sweden') == j2o(1700, 2, 28)
    for y, m, d in ((1700, 2, 29), (1700, 3, 1), (1705, 6, 1), (1712, 2, 29)):
        with pytest.raises(FeastError, match='Swedish calendar of 1 Mar 1700'):
            to_ord(y, m, d, 'sweden')
    for yr in range(1700, 1712):
        with pytest.raises(FeastError, match='Swedish calendar'):
            easter_of(yr, 'sweden')
    with pytest.raises(FeastError, match='Swedish calendar'):
        resolve('Septuagesima 1712', cal='sweden')
    assert to_ord(1712, 3, 1, 'sweden') == j2o(1712, 3, 1)
    assert feast_date('Pasch. 1712', cal='sweden') == 'Sun 20 Apr 1712 (Julian)'


def test_explicit_switch_is_the_preset():
    given = calendar_of('1752-09-02:1752-09-14')
    for yr in range(1740, 1770):
        assert easter_of(yr, given) == easter_of(yr, 'england')
        assert resolve('Dom. 1. Adv.', yr, given) == resolve('Dom. 1. Adv.', yr, 'england')
    with pytest.raises(FeastError, match='does not exist in the given calendar'):
        to_ord(1752, 9, 10, given)


@pytest.mark.parametrize('bad, why', [
    ('1752-09-02:1752-09-13', r'not a switch: the day after 2 Sep 1752 \(Julian\) is 14 Sep'),
    ('1752-09-02:1752-09-15', 'not a switch'),
    ('1752-02-30:1752-03-12', 'last Julian day 1752-02-30 does not exist'),
    ('1752-13-01:1752-09-14', 'does not exist'),
    ('mars', 'unknown calendar'),
    ('1752-09-02', 'unknown calendar'),
])
def test_bad_switch_is_refused(bad, why):
    with pytest.raises(FeastError, match=why):
        calendar_of(bad)


def test_switch_constructor_checks_the_pair():
    with pytest.raises(FeastError, match='not a switch'):
        Switch('x', 'x', (1700, 2, 18), (1700, 2, 28))


@pytest.mark.parametrize('key', sorted(SWITCH_DAYS))
def test_name_of_round_trips_across_each_switch(key):
    """Every day from two years before a switch to two after it: every name resolves back
    to its day, and every Sunday has one."""
    y0 = calendar_of(key).first_greg[0]
    for o in range(j2o(y0 - 2, 1, 1), g2o(y0 + 3, 1, 1)):
        y, m, d = ymd(o, key)
        names = name_of(y, m, d, key)
        for name, _gloss in names:
            assert resolve(name, y, key)[0] == o, (name, y, m, d, key)
        if o % 7 == 6:
            assert names, ('nameless Sunday', y, m, d, key)


def test_cli_switch(capsys):
    assert main(['--switch', 'england', 'Michaelis 1752']) == 0
    assert capsys.readouterr().out == ('Michaelis 1752 = Fri 29 Sep 1752 (Gregorian)   '
                                       '[fixed feast 29 Sep]\n')
    assert main(['--switch', '1610-08-22:1610-09-02', '--easter', '1611']) == 0
    assert capsys.readouterr().out == 'Easter 1611 = Sun 3 Apr 1611 (Gregorian)\n'
    assert main(['--switch', 'sweden', '--iso', 'Pasch. 1744']) == 0
    assert capsys.readouterr().out == '1744-03-18 J\n'


def test_cli_switch_refusals(capsys):
    assert main(['--switch', 'prussia-duchy', '--easter', '1724']) == 2
    assert 'not established' in capsys.readouterr().err
    assert main(['--switch', 'england', '--json', '--date', '1752-09-10']) == 2
    out = json.loads(capsys.readouterr().out)
    assert 'does not exist in the British calendar' in out['error']
    with pytest.raises(SystemExit) as e:
        main(['--switch', 'mars', 'Pasch. 1700'])
    assert e.value.code == 2
    with pytest.raises(SystemExit):
        main(['--switch', 'england', '--gregorian', 'Pasch. 1700'])
