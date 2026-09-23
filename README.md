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
pip install feastdate
```

Or the latest `main` straight from GitHub:

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

$ feastdate --switch england "Michaelis 1752"
Michaelis 1752 = Fri 29 Sep 1752 (Gregorian)   [fixed feast 29 Sep]
```

### The reverse: what did the register call this day?

An index gives `26 Jul 1657`, and you want to know whether the register's `Dom. 9. Trin.`
agrees. `--date` names the day:

```console
$ feastdate --date 1657-07-26
26 Jul 1657 (Julian) = Sun   Dom. 9. p. Trin. (9th Sunday after Trinity)

$ feastdate --date 1724-04-06
6 Apr 1724 (Gregorian) = Thu   Die Viridium (Maundy Thursday)

$ feastdate --date 1680-04-14
14 Apr 1680 (Julian) = Wed   Feria 4 post Pascha (Wednesday after Easter)

$ feastdate --date 1656-11-30
30 Nov 1656 (Julian) = Sun   Dom. 1. Adv. (1st Sunday of Advent); Andreae (St Andrew)

$ feastdate --date 1657-07-28
28 Jul 1657 (Julian) = Tue   no name of its own: the week of Dom. 9. p. Trin.
```

The date is read in the calendar in force on it, the same rule the forward direction uses:
under the default, Julian before 1 Mar 1700, so `--date 1700-02-24` is refused as a day that
never happened. `--gregorian`, `--julian` and `--switch` apply to the date as well.

Every name printed is in a form `feastdate` reads back to the same day, followed by an English
gloss. A day can have several names. Every Sunday has at least one, and so does every day from
Septuagesima to the week of Trinity (a weekday there is a feria counted from its Sunday:
`Feria 4 post Jubilate`). A weekday in the rest of the year has a name only if it is a saint's
day; otherwise the output says which week it is in. That line is a description, not a register
form: a feria is counted only from a Sunday without a number, so `Feria 3 post Dom. 9. p.
Trin.` is not something `feastdate` reads. Corpus Christi and the Sundays after Pentecost are
named under `--gregorian` and `--switch catholic` only, and `Totensonntag` under the default
(and `--switch prussia-duchy`) from 1816.

You can put the year in the text or give it as a separate argument. A year inside the text
is recognised from 1500 to 1899, so that a number such as the `9` in `Dom. 9. Trin.` is read as
an ordinal. Give any other year, from 100 to 9999, as a separate last argument: a shorter
number there is still read as an ordinal, since `feastdate "Dom. Trin." 9` could mean either.
(`--easter` takes any year from 1 to 9999, and so does the `year` argument of the Python API.) The bracketed part of
the output shows what the parser recognised, so you can check it read the entry the way you
meant. If it recognises nothing, it prints an error and exits with status 2.

| Option | Meaning |
| --- | --- |
| *(none)* | Protestant German calendar (see below) |
| `--gregorian` | Gregorian throughout, for Catholic parishes |
| `--julian` | Julian throughout |
| `--switch TERRITORY` | another territory's switch: `england`, `sweden`, ... or `LAST:FIRST` (see below) |
| `--easter YEAR` | Easter Sunday of that year |
| `--date YYYY-MM-DD` | the reverse: the church-year names of that day |
| `--iso` | only the date and calendar letter: `1656-03-30 J` |
| `--json` | one JSON object per entry |
| `-` | read one entry per line from stdin |

### Many entries at once, and output for scripts

`--iso` prints only the date, as `YYYY-MM-DD` followed by `J` (Julian) or `G` (Gregorian).
`--json` prints one object per entry. A refusal is an object with an `error` key instead,
and the exit status is still 2:

```console
$ feastdate --iso "Dom. Palm. 1656"
1656-03-30 J

$ feastdate --json "Dom. Palm. 1656"
{"input": "Dom. Palm. 1656", "date": "1656-03-30", "calendar": "Julian", "weekday": "Sun", "jdn": 2326001, "parsed": "palm"}

$ feastdate --json "Dom. Palm."
{"input": "Dom. Palm.", "error": "no year: give one, e.g. \"Dom. Palm. 1656\""}
```

`jdn` is the Julian Day Number, the same day whichever calendar printed it. `--json` works
with `--easter` and with `--date`, which gives the names as a list of `name` and `gloss` pairs.

To convert a whole extraction, give `-` as the text, or no text with stdin redirected, and
put one entry on each line. If the year is kept in its own column, put it after a tab. Every
input line gives one output line, including a refused line, so the output lines up with the
input. Each refusal is also reported on stderr with its line number. The exit status is 0 only
if every line resolved, and 2 otherwise:

```console
$ printf 'Dom. Palm. 1656\nDom. Palm.\nDom. 9. Trin.\t1950\n' | feastdate --iso -
1656-03-30 J
feastdate: line 2: no year: give one, e.g. "Dom. Palm. 1656"
error: no year: give one, e.g. "Dom. Palm. 1656"
1950-08-06 G
```

The default single-entry output line has not changed.

## Python

```python
>>> from feastdate import feast_date, resolve, easter, fmt, name_of
>>> feast_date("Dom. Lætare", 1680)
'Sun 21 Mar 1680 (Julian)'
>>> feast_date("Pasch.", 1744, cal="G")
'Sun 5 Apr 1744 (Gregorian)'
>>> resolve("Whit Monday 1735")          # (Julian Day Number, what was recognised)
(2354905, 'whit + 1 day(s)')
>>> fmt(easter(1656))
'6 Apr 1656'
>>> name_of(1656, 11, 30)                # the reverse lookup
[('Dom. 1. Adv.', '1st Sunday of Advent'), ('Andreae', 'St Andrew')]
```

| Function | Returns |
| --- | --- |
| `feast_date(text, year=None, cal='P')` | the formatted date, e.g. `'Sun 30 Mar 1656 (Julian)'` |
| `resolve(text, year=None, cal='P')` | `(julian_day_number, description)`; raises `FeastError` |
| `name_of(y, m, d, cal='P')` | every name of that day, `[(name, gloss), ...]`, movable days first; each one resolves back to the day |
| `week_of(y, m, d, cal='P')` | `(weekday, name of the Sunday that begins its week)`, e.g. `('Tue', 'Dom. 9. p. Trin.')` |
| `ymd(jdn, cal)` | a Julian Day Number as `(y, m, d)` in the calendar in force on that day |
| `show(jdn, cal)` | a Julian Day Number formatted in the calendar in force on that day |
| `easter(y)` | Easter Sunday as a Julian Day Number, by the Protestant German reckoning |
| `easter_of(y, cal)` | Easter Sunday under `cal` (`'P'`, `'G'`, `'J'` or a switch) |
| `calendar_of(cal)` | `cal` as the module takes it: `'G'`, `'J'` or a `Switch`; raises `FeastError` for an unknown name or a pair of days that are not consecutive |
| `SWITCHES`, `Switch` | the named switches, and the class to build your own |
| `is_greg(jdn, cal)` | whether that day is reckoned in the Gregorian calendar under `cal` |
| `julian_easter(y)`, `greg_easter(y)` | `(month, day)` of Easter in that calendar |
| `j2o`, `o2j`, `g2o`, `o2g` | Julian or Gregorian `(y, m, d)` to and from a Julian Day Number |
| `to_ord(y, m, d, cal)` | a fixed date as a Julian Day Number, in the calendar in force on that day; raises `FeastError` for a day that never existed (19 to 29 Feb 1700 under `'P'`) |
| `cal_of_year(y, cal, m=None, d=None)` | `'J'` or `'G'`: the calendar a fixed date is reckoned in |
| `is_leap(y, c)` | whether `y` is a leap year in calendar `c` (`'J'` or `'G'`) |
| `fmt(jdn)` | `'30 Mar 1656'`: Julian before 1 Mar 1700, Gregorian from it |
| `FE` | movable feasts as day offsets from Easter Sunday, e.g. `FE['Trinity'] == 56` |

Every function that takes `cal` also takes a switch name (`cal='england'`), an explicit
`'1752-09-02:1752-09-14'`, or a `Switch`.

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

### Other territories: `--switch`

Other territories changed calendar at other times. `--switch` takes one of these, or the two
days of any switch written `LAST:FIRST`: the last Julian day, then the first Gregorian day.

| `--switch` | Last Julian day | First Gregorian day | Easter |
| --- | --- | --- | --- |
| `de-protestant` | 18 Feb 1700 | 1 Mar 1700 | the default, `'P'`: 9 Apr 1724 and 29 Mar 1744 |
| `denmark-norway` | 18 Feb 1700 | 1 Mar 1700 | as `de-protestant`, 1724 and 1744 included |
| `prussia-duchy` | 22 Aug 1610 | 2 Sep 1610 | Gregorian from 1611; **1724 and 1744 are refused** |
| `sweden` | 17 Feb 1753 | 1 Mar 1753 | astronomical from 1740: 18 Mar 1744 (Julian), 25 Apr 1802, 21 Apr 1805, 29 Mar 1818; **1 Mar 1700 to 30 Feb 1712 is refused** |
| `england`, `british-colonies` | 2 Sep 1752 | 14 Sep 1752 | Gregorian from 1753 |
| `catholic` | 4 Oct 1582 | 15 Oct 1582 | Gregorian from 1583 |

```console
$ feastdate --switch 1752-09-02:1752-09-14 "Dom. 15. p. Trin." 1752
Dom. 15. p. Trin. 1752 = Sun 17 Sep 1752 (Gregorian)   [15. Sunday after Trinity]
```

The rules for every switch:

* **A date is read in the calendar in force on that day**, as under the default: `Michaelis
  1752` under `england` is Gregorian 29 September, and `Pasch. 1752` is Julian 29 March. The
  days a switch dropped (3 to 13 September 1752 under `england`) are refused.
* **Easter is Julian before the switch and Gregorian after it.** In the year of the switch
  the Gregorian Easter is used only if it falls on or after the first Gregorian day. So
  England kept a Julian Easter in 1752, and Sweden a Gregorian one in 1753.
* **The two days of `LAST:FIRST` must be consecutive**, or the switch is refused: the day
  after Julian 2 Sep 1752 is Gregorian 14 Sep, so `1752-09-02:1752-09-13` is an error. An
  explicit switch has no Easter exceptions.

What each preset models, and why:

* **`denmark-norway`** changed with the Protestant estates of the Empire, and kept the same
  astronomical Easter of the Improved Calendar, so its Easter was a week before the Gregorian
  one in 1724 and 1744 too.
* **`prussia-duchy`** (Ducal, later East, Prussia) followed its Polish overlord in 1610. It is
  **not established** here whether it then kept the Protestant Easter of 1724 and 1744 with
  the other Protestant estates, or the Gregorian Easter it had kept since 1611. Those two
  Easters, and every movable feast of those two years, are refused. Pick
  `--switch de-protestant` or `--gregorian` once you know which the parish kept.
* **`sweden`** (with Finland until 1809) is the most complicated. From 1 Mar 1700 to 30 Feb
  1712 Sweden used its own calendar, one day ahead of the Julian. **feastdate does not model
  that calendar, and refuses every date in it**, rather than give a weekday that is a day
  off. From 1740, still in the Julian calendar, Sweden computed Easter astronomically as the
  Improved Calendar did. It kept that until 1844, so its Easter was a week before the
  Gregorian one in 1744 (18 Mar 1744, Julian) and a week after it in 1802, 1805 and 1818. By
  the same computation 1825 and 1829 should have been late too, but Sweden kept the Gregorian
  date in those years, and so does `feastdate`. Finland after 1809 is not modelled.
* **`england`** follows the Calendar (New Style) Act 1750, for Great Britain and its colonies.
  The same Act moved the start of the year from 25 March to 1 January, from 1752. Before then
  an English date from 1 January to 24 March is written with two years, `1680/81`.
  `feastdate` reads a year the modern way, starting 1 January, so **give the later year**:
  `Candlemas 1680/81` is `Purif. 1681`.
* **`catholic`** is the switch of *Inter gravissimas*, followed by Spain, Portugal, Poland and
  most of Italy. Many Catholic territories changed a few weeks or years later (France in
  December 1582, most Catholic German states in 1583 to 1585): give those as `LAST:FIRST`.
  Unlike `--gregorian`, it is Julian before the switch.
* **The Protestant Swiss cantons** changed in 1701, 1724 and as late as 1812, canton by canton.
  There is no preset for them: give the canton's two days as `LAST:FIRST`.

Sources: the switch days are those of the
[list of Gregorian adoption dates](https://en.wikipedia.org/wiki/List_of_adoption_dates_of_the_Gregorian_calendar_by_country)
and Claus Tøndering's
[calendar tables](https://www.webexhibits.org/calendars/year-countries.html). The Easter dates
of the Improved Calendar, and the territories that kept them in 1724, 1744, 1802, 1805, 1818,
1825 and 1829, are from R. H. van Gent's
[table of anomalous Easter dates](https://webspace.science.uu.nl/~gent0113/easter/easter_text3b.htm)
(Utrecht University), and the Swedish ones also from the
[Swedish calendar](https://en.wikipedia.org/wiki/Swedish_calendar) article. These are secondary
sources. Grotefend's *Zeitrechnung* is the standard reference, and a date it gives
differently is a bug worth filing.

## Accepted spellings

The parser tolerates the abbreviations and punctuation registers actually use. Case is
ignored, `æ`/`ä`/`ö`/`ü`/`ß` are folded, and punctuation is ignored. Each word matches by
its **beginning**, so `Reminisc.`, `Reminisc:` and `Reminiscere` all mean the same Sunday.

| Day | Offset from Easter | Recognised by the word beginning with |
| --- | --- | --- |
| Septuagesima | −63 | `septuag` |
| Sexagesima | −56 | `sexag` |
| Estomihi / Quinquagesima | −49 | `estomihi`, `esto`, `quinq`, `fastnacht` |
| Shrove Tuesday | −47 | `fastnachtsdienstag`, `fastnacht dienstag` (Estomihi and a weekday, below) |
| Ash Wednesday | −46 | `aschermittw`, `cinerum` (`Dies Cinerum`, `Feria IV Cinerum`), `ash wednes` |
| Invocavit | −42 | `invoc` |
| Reminiscere | −35 | `reminisc` |
| Oculi | −28 | `oculi` |
| Laetare | −21 | `laetare`, `laet`, `lat` (so `Lætare`, `Lätare`) |
| Judica | −14 | `judica` |
| Palm Sunday | −7 | `palm` |
| Maundy Thursday | −3 | `viridium`, `coena`, `cena`, `grundonnerstag`, `maundy` |
| Good Friday | −2 | `parasceve`, `karfreitag`, `charfreitag`, `good` |
| Holy Saturday | −1 | `karsamstag`, `charsamstag`, `karsonnabend`, `ostersamstag`, `ostersonnabend`, `oster samstag`, `sabbat sanct` (`Sabbatho Sancto`), `holy sat` |
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
| Corpus Christi | +60 | `fronleichnam`, `corp christi` (`Corporis Christi`, `Corpus Christi`) |

A name of two words, such as `sabbat sanct`, matches the two words in order, with only
connecting words between them (see *Fixed feasts* below).

`Ostersamstag` and `Ostersonnabend` are the Saturday **before** Easter, not after it.

**Corpus Christi is a Catholic feast.** It resolves under every calendar, the default
included, because the date is the same. A Protestant register naming it is usually dating
by a neighbouring Catholic parish's calendar, so consider `--gregorian`.

**Buß- und Bettag is not recognised, on purpose.** Its date varied by territory and
century, so no single rule gives it, and `feastdate` refuses it rather than guess.

**Numbered Sundays** take an Arabic or Roman ordinal, with or without an ending
(`9.`, `9th`, `IX`, `2da`):

* `Dom. 9. Trin.`, `Dom XXIII post Trin.`, `9th Sunday after Trinity` give the *n*th Sunday
  after Trinity.
* `Dom. 1. Adv.` to `Dom. 4. Adv.` give the Sundays of Advent, counted back from Christmas.
* `Dom. 5. p. Epiph.` gives the *n*th Sunday after Epiphany. `Epiphany` alone gives 6 January.
* `Dom. 5. post Pent.`, `Dominica 5. post Pentecosten` and `Dom. 5. nach Pfingsten` give the
  *n*th Sunday after Pentecost, the count of Catholic registers and of Protestant ones before
  the Trinity count took hold. `Dom. 1. post Pent.` is Trinity Sunday, so `Dom. 5. post Pent.`
  is `Dom. 4. p. Trin.`. A year has 23 to 28 of them, one more than the Sundays after Trinity.
* `Dom. ult. p. Trin.`, `Dom. ult. Trin.`, `letzter Sonntag nach Trinitatis` and
  `Dom. ultima post Pent.` give the last Sunday after Trinity or Pentecost, a week before
  Advent 1: in 1680, `Dom. 24. p. Trin.`.
* `Totensonntag` and `Ewigkeitssonntag` are the same Sunday, but Prussia named it only in
  1816, so `Totensonntag 1815` is refused. Before 1816, write `Dom. ult. p. Trin.`.
* The count is checked against the year. The Sundays after Trinity run up to Advent, so a year
  has 22 to 27 of them (23 to 28 counted after Pentecost), and the Sundays after Epiphany run up to Septuagesima, 1 to 6. A
  Sunday the year did not have is refused, not carried into Advent or Lent:

  ```console
  $ feastdate "Dom. 26. Trin. 1680"
  feastdate: there were 24 Sundays after Trinity in 1680, not 26 in 'Dom. 26. Trin. 1680'
  ```

**Weekdays after a feast:**

* `Fer. 2. Pent.`, `Feria 2da Paschat.` and `Fer. 3. Pasch.` use the feria count, where 2 is
  Monday and 3 is Tuesday. A feria outside 1 to 7 is refused.
* `Whit Monday`, `Easter Tuesday`, `Ostermontag` and `Pfingstdienstag` are also understood,
  with the weekday written as part of the word or as a separate word. The weekday counts
  from a Sunday feast only: `Fastnachtsdienstag` is Estomihi plus two days, and
  `Karfreitag Montag` is refused.
* `Feria secunda`, `Fer. tertia` spell the number out; `prima` to `septima` are understood.
* With a feast that is not a Sunday, the feria names that feast's own weekday, where 1 is
  Sunday: `Feria 6 in Parasceve` is Good Friday and `Feria V in Coena Domini` is Maundy
  Thursday. Nothing is added to the date. The number is checked instead, so
  `Fer. 2. Ascens.` is refused, because Ascension is a Thursday.

**A day counted from a feast:** the day stands before `nach`, `post`, `p.` or `after`
(or `vor`, `ante`, `before`), and the feast after it. The answer is the first such day
strictly after the feast, or the last one strictly before it:

```console
$ feastdate "Freitag nach Jubilate 1680"
Freitag nach Jubilate 1680 = Fri 7 May 1680 (Julian)   [Friday after jubilate]
```

* `Freitag nach Jubilate`, `Mittwoch nach Oculi`, `Montag nach Trinitatis` and
  `Sonnabend vor Palmarum` name the weekday. `Feria 4 post Oculi` and `Fer. 6 p. Reminisc.`
  name it by the feria, where 1 is Sunday.
* `Dom.` names the Sunday: `Dom. p. Nativ.`, `Sonntag nach Michaelis`, `Dom. post Martini`,
  `Dom. ante Circumcis.`. Strictly after means that when Michaelmas is itself a Sunday, as
  in 1689, `Sonntag nach Michaelis` is the Sunday a week later.
* `Dom. post Pascha` and `Dom. 1. post Pascha` are Quasimodogeniti, and `Dom. 2. p. Pasch.`
  is Misericordias, up to `Dom. 6. post Pascha`. Easter, Pentecost, Trinity and Epiphany
  are the only feasts whose Sundays are numbered (see *Numbered Sundays* above).
* The year is the feast's: `Dom. post Nativ. 1740` is Sunday 1 January 1741.
* A weekday word after the feast still checks or moves the feast, so `Freitag nach
  Ostermontag` is the Friday after Easter Monday. One `nach` at a time: `Freitag nach Dom.
  post Oculi` is refused.

**Days of a German feast:** Easter, Whitsun and Christmas were kept over several days, and
German registers count them:

* `2. Ostertag`, `der 2te Ostertag`, `2ter` or `zweiter Ostertag` is Easter Monday, and
  `3. Ostertag` or `der dritte Ostertag` is Easter Tuesday. `Osterfeiertag` and `Oster Tag`
  are the same.
* `2. Pfingsttag` is Whit Monday. `2. Weihnachtstag` and `2. Christtag` are 26 December.
* `letzter Ostertag` is the third day, as the registers use it.
* A feast was kept three days at most, so `4. Ostertag` is refused.

**Fixed feasts** give you the weekday too. A name of two words, such as `mariae verk`,
matches those two words in order, with only connecting words (`et`, `und`, `S.`) between
them, and it wins over a one-word name on either word: `Nativ. Mariae` is 8 September,
not Christmas, `Mariae Himmelfahrt` is 15 August, not Ascension, and `Johannis Evang.` is
27 December, not 24 June.

| Feast | Date | Recognised by |
| --- | --- | --- |
| Circumcision / New Year | 1 Jan | `circumcis`, `neujahr` |
| Conversion of St Paul | 25 Jan | `pauli bekehr`, `bekehr pauli`, `convers pauli` |
| Purification (Candlemas) | 2 Feb | `purif`, `lichtmess` |
| St Matthias | 24 Feb, **25 Feb in a leap year** | `matthia`, `mathia` |
| St Gregory | 12 Mar | `gregor` |
| Annunciation | 25 Mar | `annunc`, `mariae verk` |
| St George | 23 Apr | `georg` |
| SS Philip and James / Walpurgis | 1 May | `philippi jac`, `phil jac`, `walpurg` |
| Finding of the Cross | 3 May | `kreuzerfind`, `kreuz erfind`, `invent cruc` |
| St John the Baptist | 24 Jun | `johannis`, `joh bapt` |
| SS Peter and Paul | 29 Jun | `petri pauli`, `peter paul` |
| Visitation | 2 Jul | `visitat`, `heimsuch` |
| St Mary Magdalene | 22 Jul | `magdalen` |
| St James | 25 Jul | `jacob` |
| St Lawrence | 10 Aug | `laurent` |
| Assumption | 15 Aug | `assumpt`, `mariae himmelf`, `himmelf mariae` |
| St Bartholomew | 24 Aug | `bartholom` |
| Nativity of Mary | 8 Sep | `nativ mariae`, `mariae geburt` |
| Exaltation of the Cross | 14 Sep | `kreuzerhoh`, `kreuz erhoh`, `exalt cruc` |
| St Matthew | 21 Sep | `matthae`, `matthai`, `matthau`, `mathae` |
| Michaelmas | 29 Sep | `michael` |
| St Gall | 16 Oct | `galli`, `gallus` |
| SS Simon and Jude | 28 Oct | `simon jud` |
| All Saints | 1 Nov | `omnium sanct`, `allerheilig` |
| All Souls | 2 Nov | `omnium anim`, `allerseel` |
| Martinmas | 11 Nov | `martini` |
| St Elisabeth | 19 Nov | `elisab` |
| St Andrew | 30 Nov | `andreae`, `andreas` |
| St Thomas | 21 Dec | `thomae`, `thomas` |
| Christmas | 25 Dec | `nativ`, `christtag`, `weihnacht`, `christmas` |
| St Stephen | 26 Dec | `stephan` |
| St John the Evangelist | 27 Dec | `johannis evang`, `joh evang` |
| Holy Innocents | 28 Dec | `innocent`, `unschuld`, `kindlein` |

A saint's epithet is a connecting word: `Andreae Apost.`, `Matthaei Apost. et Evang.`,
`Michaelis Archangeli`, `Laurentii Martyr.` (`apost`, `evang`, `archang`, `martyr`, `virg`,
`episc`).

**St Matthias and the leap day.** The Julian calendar counted its leap day in by doubling
24 February (the *bissextile* day), so in a leap year the feasts after it moved a day
later, and German almanacs, Protestant and Catholic, kept Matthias on **25 February in a
leap year** long after 1700. `feastdate` follows that reckoning for any feast from 24 to
28 February, which in this table is Matthias alone. The leap year is the one of the
calendar in force on the day: 1800 is a leap year in the Julian calendar but not in the
Gregorian, so `Matthiae 1800` is 24 February by default and 25 February with `--julian`.
The label says when the rule applied:

```console
$ feastdate "Matthiae 1680"
Matthiae 1680 = Wed 25 Feb 1680 (Julian)   [fixed feast 25 Feb, leap year]
```

Under the default rules there was no St Matthias in 1700, since 18 February (Julian) was
followed by 1 March, and `Matthiae 1700` is refused.

**Nothing is skipped.** Every word and number in the text must be accounted for: a feast
name, a number the feast uses, a weekday that agrees with the answer, a day counted from
the feast (`Freitag nach`), or a connecting word (`Dom.`, `Festo`, `der`, `Domini` and the
like). Anything else is an error, never
dropped, so the answer is not a plausible date that ignored part of what you typed:

```console
$ feastdate "2. Ostern 1747"
feastdate: the number 2 is not used by ostern in '2. Ostern 1747': a day of the feast is written "2. Ostertag" or "Fer. 2. Pasch."

$ feastdate "Dom. Oculi = 4 March 1638"
feastdate: unrecognised word in 'Dom. Oculi = 4 March 1638': march
```

Pass the feast name alone, not the whole sentence around it. A weekday word is a check,
unless it stands before `nach` / `post` / `vor`: `Good Friday` must fall on a Friday, and
`Dominica Viridium` is refused, because Maundy Thursday is not a Sunday.

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
  in 1600–1799, in all three calendars, falls on a Sunday. It also runs the reverse lookup
  over every day of those two centuries and resolves each name it gives back to the same day,
  so the two directions cannot drift apart.

## Development

```console
pip install -e ".[test]"
pytest
```

## License

MIT. See [LICENSE](https://github.com/isaacschepp/feastdate/blob/main/LICENSE).
