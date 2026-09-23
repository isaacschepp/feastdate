"""feastdate: church-year feast names (``Dom. Palm. 1656``) -> calendar dates.

    >>> from feastdate import feast_date
    >>> feast_date("Dom. 9. Trin.", 1657)
    'Sun 26 Jul 1657 (Julian)'
"""
from .core import (  # noqa: F401
    DAY, FE, MON, SWITCH, FeastError, cal_of_year, easter, easter_of, feast_date, fmt,
    g2o, greg_easter, is_leap, j2o, julian_easter, name_of, o2g, o2j, resolve, show, to_ord,
    week_of, ymd,
)

__version__ = '1.5.0'

__all__ = [
    'feast_date', 'resolve', 'show', 'FeastError', 'name_of', 'week_of', 'ymd',
    'easter', 'easter_of', 'julian_easter', 'greg_easter',
    'j2o', 'o2j', 'g2o', 'o2g', 'to_ord', 'cal_of_year', 'is_leap', 'fmt',
    'FE', 'MON', 'DAY', 'SWITCH', '__version__',
]
