# feastdate

Old parish registers often date an entry by the church year rather than the calendar:
*baptised Dom. Palm. 1656*, *buried Dom. 9. Trin.*, *married Fer. 2. Pent.* `feastdate`
turns those into calendar dates, gives the weekday, and says which calendar the date is in.

```console
$ feastdate "Dom. Palm. 1656"
Dom. Palm. 1656 = Sun 30 Mar 1656 (Julian)   [palm]

$ feastdate "Dom. 9. Trin." 1657
Dom. 9. Trin. 1657 = Sun 26 Jul 1657 (Julian)   [9. Sunday after Trinity]

$ feastdate "Fer. 2. Pent. 1724"
Fer. 2. Pent. 1724 = Mon 29 May 1724 (Gregorian)   [pent + 1 day(s)]
```

It is pure Python, uses only the standard library, and runs on Python 3.9 or later.

## Install

```console
pip install git+https://github.com/isaacschepp/feastdate
```

This gives you a `feastdate` command, and `python -m feastdate` does the same thing.

## Command line

```console
$ feastdate "Dom XXIII post Trin. 1690"
Dom XXIII post Trin. 1690 = Sun 23 Nov 1690 (Julian)   [23. Sunday after Trinity]

$ feastdate "Die Viridium 1724"
Die Viridium 1724 = Thu 6 Apr 1724 (Gregorian)   [viridium]

$ feastdate "Festo Michaelis 1699"
Festo Michaelis 1699 = Fri 29 Sep 1699 (Julian)   [fixed feast 29 Sep]

$ feastdate --easter 1744
Easter 1744 = Sun 29 Mar 1744 (Gregorian)

$ feastdate --gregorian --easter 1744
Easter 1744 = Sun 5 Apr 1744 (Gregorian)

$ feastdate --gregorian "Dom. 1. Adv. 1650"
Dom. 1. Adv. 1650 = Sun 27 Nov 1650 (Gregorian)   [1. Sunday of Advent]
```

You can put the year in the text or give it as a separate argument. A year inside the text
is recognised from 1500 to 1899, so that a number such as the `9` in `Dom. 9. Trin.` is read as
an ordinal. Give any other year, from 1 to 9999, as a separate last argument. The bracketed part of
the output shows what the parser recognised, so you can check it read the entry the way you
meant. If it recognises nothing, it prints an error and exits with status 2.

| Option | Meaning |
| --- | --- |
| *(none)* | Protestant German calendar (see below) |
| `--gregorian` | Gregorian throughout, for Catholic parishes |
| `--julian` | Julian throughout |
| `--easter YEAR` | Easter Sunday of that year |

## Python

```python
>>> from feastdate import feast_date, resolve, easter, fmt
>>> feast_date("Dom. Lætare", 1680)
'Sun 21 Mar 1680 (Julian)'
>>> feast_date("Pasch.", 1744, cal="G")
'Sun 5 Apr 1744 (Gregorian)'
>>> resolve("Whit Monday 1735")          # (Julian Day Number, what was recognised)
(2354905, 'whit + 1 day(s)')
>>> fmt(easter(1656))
'6 Apr 1656'
```

| Function | Returns |
| --- | --- |
| `feast_date(text, year=None, cal='P')` | the formatted date, e.g. `'Sun 30 Mar 1656 (Julian)'` |
| `resolve(text, year=None, cal='P')` | `(julian_day_number, description)`; raises `FeastError` |
| `show(jdn, cal)` | a Julian Day Number formatted in the calendar in force on that day |
| `easter(y)` | Easter Sunday as a Julian Day Number, by the Protestant German reckoning |
| `easter_of(y, cal)` | Easter Sunday under `cal` (`'P'`, `'G'` or `'J'`) |
| `julian_easter(y)`, `greg_easter(y)` | `(month, day)` of Easter in that calendar |
| `j2o`, `o2j`, `g2o`, `o2g` | Julian or Gregorian `(y, m, d)` to and from a Julian Day Number |
| `to_ord(y, m, d, cal)` | a fixed date as a Julian Day Number, in the calendar in force on that day; raises `FeastError` for a day that never existed (19 to 29 Feb 1700 under `'P'`) |
| `cal_of_year(y, cal, m=None, d=None)` | `'J'` or `'G'`: the calendar a fixed date is reckoned in |
| `fmt(jdn)` | `'30 Mar 1656'`: Julian before 1 Mar 1700, Gregorian from it |
| `FE` | movable feasts as day offsets from Easter Sunday, e.g. `FE['Trinity'] == 56` |

All dates are carried internally as Julian Day Numbers, so both calendars share one number
line, and `jdn % 7` gives the weekday (0 is Monday and 6 is Sunday).

## The calendar rules

**The default (`'P'`) follows the Protestant German estates**, such as Hessen-Darmstadt,
Baden-Durlach and Brandenburg-Prussia:

* **Julian to the end of 1699.**
* **The Improved Calendar from 1700.** 18 February 1700 (Julian) was followed by 1 March
  1700, which dropped eleven days. From then on the calendar dates are Gregorian.
* **Easter in 1724 and 1744 is the exception.** The Improved Calendar computed Easter
  astronomically, not from the Gregorian tables. Its result matched the Gregorian Easter in
  every year except these two, when the Protestants kept Easter a week earlier:

  | Year | Protestant Easter | Gregorian Easter |
  | --- | --- | --- |
  | 1724 | 9 April | 16 April |
  | 1744 | 29 March | 5 April |

  Every movable feast in those two years moves with it. Parish registers confirm this: a
  Hessian register dates Maundy Thursday 1724 (*Die Viridium*) to 6 April.

**`--gregorian` (`'G'`) is for Catholic parishes.** Catholic territories adopted the
Gregorian calendar in 1582 or 1583. Before that year the option still computes Gregorian
dates, so for an earlier Catholic entry use the default or `--julian`.

**`--julian` (`'J'`) uses the Julian calendar for every year.**

Every result states its calendar, (Julian) or (Gregorian), because a date without one is
ambiguous for anything before 1700.

Other territories changed calendar at other times. England and its colonies switched in
1752, and Sweden took its own route. The default rules model only the German Protestant
switch in 1700. For other places, pick `--julian` or `--gregorian` to match the calendar in
use there on the date you need.

## Accepted spellings

The parser tolerates the abbreviations and punctuation registers actually use. Case is
ignored, `æ`/`ä`/`ö`/`ü`/`ß` are folded, and punctuation is ignored. Each word matches by
its **beginning**, so `Reminisc.`, `Reminisc:` and `Reminiscere` all mean the same Sunday.

| Day | Offset from Easter | Recognised by the word beginning with |
| --- | --- | --- |
| Septuagesima | −63 | `septuag` |
| Sexagesima | −56 | `sexag` |
| Estomihi / Quinquagesima | −49 | `estomihi`, `esto`, `quinq`, `fastnacht` |
| Invocavit | −42 | `invoc` |
| Reminiscere | −35 | `reminisc` |
| Oculi | −28 | `oculi` |
| Laetare | −21 | `laetare`, `laet`, `lat` (so `Lætare`, `Lätare`) |
| Judica | −14 | `judica` |
| Palm Sunday | −7 | `palm` |
| Maundy Thursday | −3 | `viridium`, `coena`, `cena`, `grundonnerstag`, `maundy` |
| Good Friday | −2 | `parasceve`, `karfreitag`, `charfreitag`, `good` |
| Easter | 0 | `pasch`, `ostern`, `oster`, `easter` |
| Quasimodogeniti | +7 | `quasimod`, `quasi`, `quas`, `weisser` |
| Misericordias Domini | +14 | `miseric`, `miser` |
| Jubilate | +21 | `jubil` |
| Cantate | +28 | `cantat` |
| Rogate / Vocem jucunditatis | +35 | `rogat`, `voc` |
| Ascension | +39 | `ascens`, `himmelfahrt` |
| Exaudi | +42 | `exaudi` |
| Pentecost / Whitsun | +49 | `pentecost`, `pent`, `pfingst`, `whit` |
| Trinity Sunday | +56 | `trinit`, `trin`, `dreifaltig` |

**Numbered Sundays** take an Arabic or Roman ordinal, with or without an ending
(`9.`, `9th`, `IX`, `2da`):

* `Dom. 9. Trin.`, `Dom XXIII post Trin.`, `9th Sunday after Trinity` give the *n*th Sunday
  after Trinity.
* `Dom. 1. Adv.` to `Dom. 4. Adv.` give the Sundays of Advent, counted back from Christmas.
* `Dom. 5. p. Epiph.` gives the *n*th Sunday after Epiphany. `Epiphany` alone gives 6 January.

**Weekdays after a feast:**

* `Fer. 2. Pent.`, `Feria 2da Paschat.` and `Fer. 3. Pasch.` use the feria count, where 2 is
  Monday and 3 is Tuesday.
* `Whit Monday`, `Easter Tuesday`, `Ostermontag` and `Pfingstdienstag` are also understood,
  with the weekday written as part of the word or as a separate word.

**Fixed feasts** give you the weekday too:

| Feast | Date | Recognised by |
| --- | --- | --- |
| Circumcision / New Year | 1 Jan | `circumcis`, `neujahr` |
| Purification (Candlemas) | 2 Feb | `purif`, `lichtmess` |
| Annunciation | 25 Mar | `annunc`, `mariae verk` |
| St John the Baptist | 24 Jun | `johannis`, `joh bapt` |
| Michaelmas | 29 Sep | `michael` |
| Martinmas | 11 Nov | `martini` |
| St Andrew | 30 Nov | `andreae`, `andreas` |
| Christmas | 25 Dec | `nativ`, `christtag`, `weihnacht`, `christmas` |
| St Stephen | 26 Dec | `stephan` |

A year written in the text must fall between 1500 and 1899, so that other numbers are read as
ordinals. The `year` argument accepts any year.

## Why this is tricky

* **There are two calendars, and the switch between them depends on the territory.** The same
  Sunday is ten or eleven days apart depending on which calendar the parish kept, and
  neighbouring Catholic and Protestant parishes differed for more than a century.
* **Easter is not a fixed date,** and there are three Easter rules: the Julian computus, the
  Gregorian tables, and the Protestant astronomical reckoning. The last differs from the
  Gregorian Easter only in 1724 and 1744, so an off-the-shelf Gregorian Easter function is
  silently wrong for a German Protestant register in exactly those two years.
* **The year 1700 is split.** For a Protestant parish, January and most of February 1700 are
  Julian and the rest of the year is Gregorian, so a date in 1700 has to know which side of
  18 February it falls on.
* **Advent and Epiphany Sundays hang off fixed dates, not Easter.** Advent 1 is the fourth
  Sunday before Christmas Day, so it falls between 27 November and 3 December. A Sunday
  "after Epiphany" is strictly after 6 January, so when 6 January is itself a Sunday, the
  first Sunday after Epiphany is the 13th.
* **Registers abbreviate freely** (`Dom. Miser. Dni.`, `Dom. Voc. jucund.`), mix Latin and
  German, and write ordinals in Roman or Arabic numerals with Latin endings.
* **A hand-copied Easter routine drifts** without anything to show it. The test suite checks
  dates against days the registers themselves settle, and checks that every computed Sunday
  in 1600–1799, in all three calendars, falls on a Sunday.

## Development

```console
pip install -e ".[test]"
pytest
```

## License

MIT. See [LICENSE](LICENSE).
