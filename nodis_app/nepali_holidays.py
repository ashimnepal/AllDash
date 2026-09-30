"""Curated Nepali holiday/festival data used by the home dashboard's Nepali calendar.

The `nepali_calendar_utils` package intentionally ships no holiday data (it only
exposes a `NepaliHolidayProvider` SPI for callers to supply their own), so this
module is our own data source.

Two kinds of entries:

- FIXED_HOLIDAYS: national holidays observed on the same Bikram Sambat
  month/day every year (e.g. the Nepali New Year is always Baisakh 1). These
  are generated for any BS year, so they stay correct for future years too.
- MOVABLE_FESTIVALS: lunar/tithi-based festivals (Dashain, Tihar, Holi, Teej,
  etc.) whose BS date shifts from year to year. These CANNOT be computed from
  the BS calendar alone (they follow the lunar Panchang), so they are hand
  populated per BS year below on a best-effort basis and should be reviewed
  against the official Nepal government calendar (Rajapatra) each year.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HolidayEntry:
    month: int  # 1 = Baisakh ... 12 = Chaitra
    day: int
    name: str
    description: str
    movable: bool = False


# National holidays fixed to the same BS month/day every year.
FIXED_HOLIDAYS = [
    HolidayEntry(1, 1, "Nepali New Year", "Beginning of the Bikram Sambat calendar year."),
    HolidayEntry(2, 15, "Republic Day", "Marks the declaration of Nepal as a federal democratic republic."),
    HolidayEntry(6, 3, "Constitution Day", "Commemorates the promulgation of the Constitution of Nepal, 2072."),
    HolidayEntry(10, 1, "Maghe Sankranti", "Marks the end of winter solstice; celebrated with til-laddu and ghee-chaku."),
    HolidayEntry(10, 16, "Martyrs' Day (Shahid Diwas)", "Honours the martyrs who sacrificed their lives for democracy."),
    HolidayEntry(11, 7, "Democracy Day (Prajatantra Diwas)", "Commemorates the 2007 BS revolution that ended Rana rule."),
]

# Best-effort dates for movable (lunar/tithi-based) festivals, per BS year.
# NOTE: these dates are approximate and should be verified against the official
# Nepal calendar each year - they are NOT computed, only curated by hand.
MOVABLE_FESTIVALS = {
    2082: [
        HolidayEntry(4, 24, "Janai Purnima / Raksha Bandhan", "Sacred thread changing and rakhi-tying day.", movable=True),
        HolidayEntry(5, 10, "Hariyali Teej", "Fasting and devotion day observed by married Hindu women.", movable=True),
        HolidayEntry(5, 19, "Gai Jatra", "Cow procession festival honouring those who passed away in the past year.", movable=True),
        HolidayEntry(5, 23, "Krishna Janmashtami", "Celebrates the birth of Lord Krishna.", movable=True),
        HolidayEntry(6, 1, "Ghatasthapana", "Marks the beginning of the Dashain festival.", movable=True),
        HolidayEntry(6, 7, "Fulpati", "Seventh day of Dashain.", movable=True),
        HolidayEntry(6, 10, "Vijaya Dashami", "The main day of Dashain, marked with tika and blessings from elders.", movable=True),
        HolidayEntry(7, 12, "Laxmi Puja (Tihar)", "Worship of the goddess of wealth during Tihar.", movable=True),
        HolidayEntry(7, 15, "Bhai Tika", "Final day of Tihar celebrating the bond between siblings.", movable=True),
        HolidayEntry(11, 19, "Maha Shivaratri", "Great night of Lord Shiva, observed with fasting and vigils.", movable=True),
        HolidayEntry(12, 4, "Fagu Purnima (Holi)", "Festival of colours.", movable=True),
    ],
    2083: [
        HolidayEntry(4, 24, "Janai Purnima / Raksha Bandhan", "Sacred thread changing and rakhi-tying day.", movable=True),
        HolidayEntry(5, 10, "Hariyali Teej", "Fasting and devotion day observed by married Hindu women.", movable=True),
        HolidayEntry(5, 19, "Gai Jatra", "Cow procession festival honouring those who passed away in the past year.", movable=True),
        HolidayEntry(6, 25, "Ghatasthapana", "Marks the beginning of the Dashain festival.", movable=True),
        HolidayEntry(6, 31, "Fulpati", "Seventh day of Dashain.", movable=True),
        HolidayEntry(7, 4, "Vijaya Dashami", "The main day of Dashain, marked with tika and blessings from elders.", movable=True),
        HolidayEntry(7, 22, "Laxmi Puja (Tihar)", "Worship of the goddess of wealth during Tihar.", movable=True),
        HolidayEntry(7, 25, "Bhai Tika", "Final day of Tihar celebrating the bond between siblings.", movable=True),
        HolidayEntry(11, 19, "Maha Shivaratri", "Great night of Lord Shiva, observed with fasting and vigils.", movable=True),
        HolidayEntry(12, 4, "Fagu Purnima (Holi)", "Festival of colours.", movable=True),
    ],
}


def get_year_holidays(bs_year):
    """Return all known holidays (fixed + movable) for a given BS year, sorted by month/day."""
    holidays = list(FIXED_HOLIDAYS) + list(MOVABLE_FESTIVALS.get(bs_year, []))
    return sorted(holidays, key=lambda h: (h.month, h.day))
