import logging
import random
from datetime import date, datetime
from datetime import timezone as dt_timezone
from urllib.parse import quote

import requests
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View
from django.views.decorators.http import require_POST
from nepali_calendar_utils import NameFormat, NepaliCalendarUtilsLang, NepaliDateConverter

from .forms import (
    CurrencyConverterForm,
    ExpenseForm,
    IncomeForm,
    MoneyToGetForm,
    MoneyToPayForm,
    NepalSavingsAddForm,
    NepalSavingsUseForm,
    PortfolioHoldingForm,
    PriceAlertForm,
)
from .models import Budget, Expense, Income, MoneyToGet, MoneyToPay
from .models import NepalSavingsTransaction, PortfolioHolding, PriceAlert
from .nepali_holidays import get_year_holidays
from .whatsapp_web import send_whatsapp_message

# Chip/legend colour used per category slug on the expense tracking page.
CATEGORY_STYLES = {
    "food": {"chip": "chip-soft-success", "legend": "legend-primary"},
    "utilities": {"chip": "chip-soft-warning", "legend": "legend-warning"},
    "transport": {"chip": "chip-soft-secondary", "legend": "legend-success"},
    "leisure": {"chip": "chip-soft-danger", "legend": "legend-danger"},
    "subscriptions": {"chip": "chip-soft-info", "legend": "legend-info"},
}
DEFAULT_CATEGORY_STYLE = {"chip": "chip-soft-secondary", "legend": "legend-secondary"}

NEPSE_API_BASE = "http://192.168.1.93:8000"
# Which real NEPSE sectorName values feed each 'My Watchlist' category pill.
WATCHLIST_SECTOR_CATEGORIES = {
    "Commercial Banks": "Banking",
    "Development Banks": "Development Bank",
    "Finance": "Finance",
    "Microfinance": "Microfinance",
    "Hydro Power": "Hydro",
    "Life Insurance": "Insurance",
    "Non Life Insurance": "Insurance",
    "Manufacturing And Processing": "Manufacturing",
    "Hotels And Tourism": "Hotels and Tourism",
    "Investment": "Investment",
    "Mutual Fund": "Mutual Funds",
}
# The 'Mutual Fund' sector has no Equity instruments - its listings are all instrumentType 'Mutual Funds'.
WATCHLIST_SECTOR_INSTRUMENT_TYPE = {
    "Mutual Fund": "Mutual Funds",
}
COMPANY_LIST_CACHE_KEY = 'nepse_company_list'
COMPANY_LIST_CACHE_TTL = 6 * 60 * 60  # the company registry barely changes, cache it longer

OPENF1_API_BASE = 'https://api.openf1.org/v1'
F1_MEETINGS_CACHE_KEY = 'openf1_meetings_{year}'
F1_MEETINGS_CACHE_TTL = 6 * 60 * 60  # the season calendar barely changes, cache it longer
F1_SESSIONS_CACHE_KEY = 'openf1_sessions_{meeting_key}'
F1_SESSIONS_CACHE_TTL = 6 * 60 * 60
F1_STANDINGS_CACHE_KEY = 'openf1_standings'
F1_STANDINGS_CACHE_TTL = 60 * 60  # standings only change once a race weekend ends
F1_SEASON_SESSIONS_CACHE_KEY = 'openf1_season_race_sessions_{year}'
F1_SEASON_SESSIONS_CACHE_TTL = 6 * 60 * 60
F1_PAST_RACES_CACHE_KEY = 'openf1_past_races_{year}'
F1_PAST_RACES_CACHE_TTL = 6 * 60 * 60  # completed race results never change


def get_f1_season_race_sessions(year):
    """Every completed Race session this season, sourced from OpenF1 /sessions."""
    cache_key = F1_SEASON_SESSIONS_CACHE_KEY.format(year=year)
    sessions = cache.get(cache_key)
    if sessions is not None:
        return sessions

    now = timezone.now()
    sessions_url = (
        f"{OPENF1_API_BASE}/sessions?year={year}&session_name=Race&date_end<={quote(now.isoformat())}"
    )
    sessions_resp = requests.get(sessions_url, timeout=10)
    sessions_resp.raise_for_status()
    sessions = sessions_resp.json()
    cache.set(cache_key, sessions, F1_SEASON_SESSIONS_CACHE_TTL)
    return sessions


def get_f1_driver_race_stats(session_keys):
    """driver_number -> {starts, wins, podiums} across the given completed Race sessions."""
    if not session_keys:
        return {}

    results_resp = requests.get(
        f'{OPENF1_API_BASE}/session_result',
        params=[('session_key', key) for key in session_keys],
        timeout=10,
    )
    results_resp.raise_for_status()

    stats = {}
    for row in results_resp.json():
        if row.get('dns'):
            continue
        entry = stats.setdefault(row['driver_number'], {'starts': 0, 'wins': 0, 'podiums': 0})
        entry['starts'] += 1
        position = row.get('position')
        if position == 1:
            entry['wins'] += 1
        if position is not None and position <= 3:
            entry['podiums'] += 1
    return stats


def get_f1_meetings(year):
    """Non-testing race weekends for a season, sorted by date, sourced from OpenF1 /meetings."""
    cache_key = F1_MEETINGS_CACHE_KEY.format(year=year)
    meetings = cache.get(cache_key)
    if meetings is not None:
        return meetings

    response = requests.get(f'{OPENF1_API_BASE}/meetings', params={'year': year}, timeout=5)
    if response.status_code == 404:
        # Next season's calendar isn't published yet - treat as "no meetings" rather than an error.
        cache.set(cache_key, [], 60 * 60)
        return []
    response.raise_for_status()
    meetings = [m for m in response.json() if 'testing' not in (m.get('meeting_name') or '').lower()]
    meetings.sort(key=lambda m: m['date_start'])
    for i, meeting in enumerate(meetings, start=1):
        meeting['round'] = i
        meeting['date_start'] = datetime.fromisoformat(meeting['date_start'])
        meeting['date_end'] = datetime.fromisoformat(meeting['date_end'])
    cache.set(cache_key, meetings, F1_MEETINGS_CACHE_TTL)
    return meetings


def get_f1_sessions(meeting_key):
    """All sessions (practice/qualifying/race) for a race weekend, sourced from OpenF1 /sessions."""
    cache_key = F1_SESSIONS_CACHE_KEY.format(meeting_key=meeting_key)
    sessions = cache.get(cache_key)
    if sessions is not None:
        return sessions

    response = requests.get(f'{OPENF1_API_BASE}/sessions', params={'meeting_key': meeting_key}, timeout=5)
    response.raise_for_status()
    sessions = response.json()
    for session in sessions:
        session['date_start'] = datetime.fromisoformat(session['date_start'])
        session['date_end'] = datetime.fromisoformat(session['date_end'])
    cache.set(cache_key, sessions, F1_SESSIONS_CACHE_TTL)
    return sessions


def get_f1_standings():
    """(driver_standings, team_standings) after the most recently completed race, sourced from OpenF1."""
    cached = cache.get(F1_STANDINGS_CACHE_KEY)
    if cached is not None:
        return cached

    session_keys = [s['session_key'] for s in get_f1_season_race_sessions(timezone.now().year)]

    # /drivers?session_key=latest misses drivers who already left the grid mid-season, so pull
    # info from every race session this year instead (a single OR-filtered request).
    driver_info = {}
    if session_keys:
        drivers_resp = requests.get(
            f'{OPENF1_API_BASE}/drivers',
            params=[('session_key', key) for key in session_keys],
            timeout=10,
        )
        drivers_resp.raise_for_status()
        for d in drivers_resp.json():
            driver_info[d['driver_number']] = d

    driver_champ_resp = requests.get(
        f'{OPENF1_API_BASE}/championship_drivers', params={'session_key': 'latest'}, timeout=5
    )
    driver_champ_resp.raise_for_status()
    driver_rows = sorted(driver_champ_resp.json(), key=lambda r: r['position_current'])

    try:
        race_stats = get_f1_driver_race_stats(session_keys)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('OpenF1 race stats fetch failed: %s', exc)
        race_stats = {}

    driver_standings = [
        {
            'position': row['position_current'],
            'name': driver_info.get(row['driver_number'], {}).get('full_name', 'Unknown'),
            'team': driver_info.get(row['driver_number'], {}).get('team_name', ''),
            'team_colour': driver_info.get(row['driver_number'], {}).get('team_colour', ''),
            'points': row['points_current'],
            'starts': race_stats.get(row['driver_number'], {}).get('starts', 0),
            'wins': race_stats.get(row['driver_number'], {}).get('wins', 0),
            'podiums': race_stats.get(row['driver_number'], {}).get('podiums', 0),
        }
        for row in driver_rows
    ]

    team_champ_resp = requests.get(
        f'{OPENF1_API_BASE}/championship_teams', params={'session_key': 'latest'}, timeout=5
    )
    team_champ_resp.raise_for_status()
    team_rows = sorted(team_champ_resp.json(), key=lambda r: r['position_current'])
    team_standings = [
        {'position': row['position_current'], 'name': row['team_name'], 'points': row['points_current']}
        for row in team_rows
    ]

    result = (driver_standings, team_standings)
    cache.set(F1_STANDINGS_CACHE_KEY, result, F1_STANDINGS_CACHE_TTL)
    return result


def get_f1_past_races(year):
    """Completed races this season with full finishing order, sourced from OpenF1."""
    cache_key = F1_PAST_RACES_CACHE_KEY.format(year=year)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    sessions = get_f1_season_race_sessions(year)
    if not sessions:
        cache.set(cache_key, [], F1_PAST_RACES_CACHE_TTL)
        return []

    session_keys = [s['session_key'] for s in sessions]
    meetings = {m['meeting_key']: m for m in get_f1_meetings(year)}

    results_resp = requests.get(
        f'{OPENF1_API_BASE}/session_result',
        params=[('session_key', key) for key in session_keys],
        timeout=10,
    )
    results_resp.raise_for_status()
    results_by_session = {}
    for row in results_resp.json():
        results_by_session.setdefault(row['session_key'], []).append(row)

    drivers_resp = requests.get(
        f'{OPENF1_API_BASE}/drivers',
        params=[('session_key', key) for key in session_keys],
        timeout=10,
    )
    drivers_resp.raise_for_status()
    driver_info = {d['driver_number']: d for d in drivers_resp.json()}

    races = []
    for session in sessions:
        meeting = meetings.get(session['meeting_key'])
        if meeting is None:
            continue
        rows = sorted(
            results_by_session.get(session['session_key'], []),
            key=lambda r: (r.get('position') is None, r.get('position') or 999),
        )
        results = [
            {
                'position': row.get('position'),
                'name': driver_info.get(row['driver_number'], {}).get('full_name', 'Unknown'),
                'team': driver_info.get(row['driver_number'], {}).get('team_name', ''),
                'team_colour': driver_info.get(row['driver_number'], {}).get('team_colour', ''),
                'dnf': bool(row.get('dnf')),
                'dns': bool(row.get('dns')),
                'dsq': bool(row.get('dsq')),
            }
            for row in rows
        ]
        races.append(
            {
                'meeting_key': meeting['meeting_key'],
                'round': meeting['round'],
                'meeting_name': meeting['meeting_name'],
                'country_name': meeting.get('country_name'),
                'date_start': meeting['date_start'],
                'results': results,
                'winner': results[0] if results else None,
            }
        )

    races.sort(key=lambda r: r['round'])
    cache.set(cache_key, races, F1_PAST_RACES_CACHE_TTL)
    return races


MOTOGP_API_BASE = 'https://api.motogp.pulselive.com/motogp/v1/results'
MOTOGP_CATEGORY_NAME = 'MotoGP™'  # premier class - Moto2/Moto3 also exist per season
MOTOGP_SEASON_CACHE_KEY = 'motogp_current_season'
MOTOGP_SEASON_CACHE_TTL = 6 * 60 * 60
MOTOGP_CATEGORY_CACHE_KEY = 'motogp_category_{season_id}'
MOTOGP_CATEGORY_CACHE_TTL = 6 * 60 * 60
MOTOGP_EVENTS_CACHE_KEY = 'motogp_events_{season_id}'
MOTOGP_EVENTS_CACHE_TTL = 6 * 60 * 60
MOTOGP_SESSIONS_CACHE_KEY = 'motogp_sessions_{event_id}_{category_id}'
MOTOGP_SESSIONS_CACHE_TTL = 6 * 60 * 60
MOTOGP_STANDINGS_CACHE_KEY = 'motogp_standings_{season_id}_{category_id}'
MOTOGP_STANDINGS_CACHE_TTL = 60 * 60
MOTOGP_PAST_RACES_CACHE_KEY = 'motogp_past_races_{season_id}_{category_id}'
MOTOGP_PAST_RACES_CACHE_TTL = 6 * 60 * 60


def get_motogp_season():
    """(season_id, year) for the current MotoGP season, sourced from pulselive /results/seasons."""
    cached = cache.get(MOTOGP_SEASON_CACHE_KEY)
    if cached is not None:
        return cached

    resp = requests.get(f'{MOTOGP_API_BASE}/seasons', timeout=5)
    resp.raise_for_status()
    seasons = resp.json()
    current = next((s for s in seasons if s.get('current')), seasons[0])
    result = (current['id'], current['year'])
    cache.set(MOTOGP_SEASON_CACHE_KEY, result, MOTOGP_SEASON_CACHE_TTL)
    return result


def get_motogp_category_id(season_id):
    """Premier-class (MotoGP) category UUID for a season, sourced from /results/categories."""
    cache_key = MOTOGP_CATEGORY_CACHE_KEY.format(season_id=season_id)
    category_id = cache.get(cache_key)
    if category_id is not None:
        return category_id

    resp = requests.get(f'{MOTOGP_API_BASE}/categories', params={'seasonUuid': season_id}, timeout=5)
    resp.raise_for_status()
    categories = resp.json()
    motogp = next((c for c in categories if c['name'] == MOTOGP_CATEGORY_NAME), categories[0])
    cache.set(cache_key, motogp['id'], MOTOGP_CATEGORY_CACHE_TTL)
    return motogp['id']


def get_motogp_events(season_id):
    """Every non-test Grand Prix this season (finished + upcoming), sorted with a computed round."""
    cache_key = MOTOGP_EVENTS_CACHE_KEY.format(season_id=season_id)
    events = cache.get(cache_key)
    if events is not None:
        return events

    resp = requests.get(f'{MOTOGP_API_BASE}/events', params={'seasonUuid': season_id}, timeout=10)
    resp.raise_for_status()
    events = [e for e in resp.json() if not e.get('test')]
    events.sort(key=lambda e: e['date_start'])
    for i, event in enumerate(events, start=1):
        event['round'] = i
        event['date_start'] = datetime.fromisoformat(event['date_start'])
        event['date_end'] = datetime.fromisoformat(event['date_end'])
    cache.set(cache_key, events, MOTOGP_EVENTS_CACHE_TTL)
    return events


def get_motogp_event_sessions(event_id, category_id):
    """All sessions (FP/Q/SPR/RAC/WUP) for one Grand Prix, sourced from /results/sessions."""
    cache_key = MOTOGP_SESSIONS_CACHE_KEY.format(event_id=event_id, category_id=category_id)
    sessions = cache.get(cache_key)
    if sessions is not None:
        return sessions

    resp = requests.get(
        f'{MOTOGP_API_BASE}/sessions',
        params={'eventUuid': event_id, 'categoryUuid': category_id},
        timeout=10,
    )
    resp.raise_for_status()
    sessions = resp.json()
    for session in sessions:
        session['date'] = datetime.fromisoformat(session['date'])
    cache.set(cache_key, sessions, MOTOGP_SESSIONS_CACHE_TTL)
    return sessions


def get_motogp_standings(season_id, category_id):
    """Rider standings (points/wins/podiums come straight from the API) + a summed constructor
    points table (pulselive has no dedicated manufacturer-standings endpoint)."""
    cache_key = MOTOGP_STANDINGS_CACHE_KEY.format(season_id=season_id, category_id=category_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    resp = requests.get(
        f'{MOTOGP_API_BASE}/standings',
        params={'seasonUuid': season_id, 'categoryUuid': category_id},
        timeout=10,
    )
    resp.raise_for_status()
    rows = sorted(resp.json().get('classification', []), key=lambda r: r['position'])

    rider_standings = [
        {
            'position': row['position'],
            'rider_id': row['rider']['id'],
            'name': row['rider']['full_name'],
            'team': row['team']['name'],
            'points': row['points'],
            'wins': row['race_wins'],
            'podiums': row['podiums'],
        }
        for row in rows
    ]

    constructor_points = {}
    for row in rows:
        constructor_name = row['constructor']['name']
        constructor_points[constructor_name] = constructor_points.get(constructor_name, 0) + row['points']
    constructor_standings = [
        {'name': name, 'points': points}
        for name, points in sorted(constructor_points.items(), key=lambda item: item[1], reverse=True)
    ]
    for i, row in enumerate(constructor_standings, start=1):
        row['position'] = i

    result = (rider_standings, constructor_standings)
    cache.set(cache_key, result, MOTOGP_STANDINGS_CACHE_TTL)
    return result


def get_motogp_past_races(season_id, category_id):
    """Completed races this season with full finishing order, sourced from pulselive classifications."""
    cache_key = MOTOGP_PAST_RACES_CACHE_KEY.format(season_id=season_id, category_id=category_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    past_events = [e for e in get_motogp_events(season_id) if e['status'] == 'FINISHED']

    races = []
    for event in past_events:
        sessions = get_motogp_event_sessions(event['id'], category_id)
        race_session = next((s for s in sessions if s.get('type') == 'RAC'), None)
        if race_session is None:
            continue
        resp = requests.get(f"{MOTOGP_API_BASE}/session/{race_session['id']}/classification", timeout=10)
        resp.raise_for_status()
        rows = resp.json().get('classification', [])

        results = [
            {
                'position': row.get('position'),
                'rider_id': row['rider']['id'],
                'name': row['rider']['full_name'],
                'team': row['team']['name'],
                'status': row.get('status'),
            }
            for row in rows
        ]
        races.append(
            {
                'event_id': event['id'],
                'round': event['round'],
                'name': event['name'],
                'country_name': event.get('country', {}).get('name'),
                'date_start': event['date_start'],
                'results': results,
                'winner': results[0] if results else None,
            }
        )

    races.sort(key=lambda r: r['round'])
    cache.set(cache_key, races, MOTOGP_PAST_RACES_CACHE_TTL)
    return races


def get_motogp_driver_starts(past_races):
    """rider_id -> number of races started, derived from get_motogp_past_races() results."""
    starts = {}
    for race in past_races:
        for row in race['results']:
            starts[row['rider_id']] = starts.get(row['rider_id'], 0) + 1
    return starts


FOOTBALL_DATA_API_BASE = 'https://api.football-data.org/v4'
FOOTBALL_DATA_PL_CODE = 'PL'
FOOTBALL_DATA_CL_CODE = 'CL'
STANDINGS_CACHE_KEY = 'football_data_{code}_standings'
STANDINGS_CACHE_TTL = 60 * 60  # standings only change once matches finish
MATCHES_CACHE_KEY = 'football_data_{code}_matches_{status}'
SCHEDULED_MATCHES_CACHE_TTL = 30 * 60
FINISHED_MATCHES_CACHE_TTL = 60 * 60
SCORERS_CACHE_KEY = 'football_data_{code}_scorers'
SCORERS_CACHE_TTL = 6 * 60 * 60  # top scorers barely move between matchdays


def _football_data_get(path, params=None):
    response = requests.get(
        f'{FOOTBALL_DATA_API_BASE}{path}',
        headers={'X-Auth-Token': settings.FOOTBALL_DATA_API_TOKEN},
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_competition_standings(code):
    """Current league table (TOTAL standings) for the given competition code, from football-data.org."""
    cache_key = STANDINGS_CACHE_KEY.format(code=code)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = _football_data_get(f'/competitions/{code}/standings')
    total_table = next(
        (s['table'] for s in data.get('standings', []) if s.get('type') == 'TOTAL'), []
    )
    cache.set(cache_key, total_table, STANDINGS_CACHE_TTL)
    return total_table


def get_competition_matches(code, status):
    """Matches for the given competition filtered by status (SCHEDULED/FINISHED/...), utcDate parsed to datetime."""
    cache_key = MATCHES_CACHE_KEY.format(code=code, status=status)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = _football_data_get(f'/competitions/{code}/matches', params={'status': status})
    matches = data.get('matches', [])
    for match in matches:
        match['kickoff'] = parse_datetime(match['utcDate'])

    ttl = SCHEDULED_MATCHES_CACHE_TTL if status == 'SCHEDULED' else FINISHED_MATCHES_CACHE_TTL
    cache.set(cache_key, matches, ttl)
    return matches


def get_competition_scorers(code, limit=10):
    """Top scorers this season for the given competition, from football-data.org."""
    cache_key = SCORERS_CACHE_KEY.format(code=code)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached[:limit]

    data = _football_data_get(f'/competitions/{code}/scorers', params={'limit': limit})
    scorers = data.get('scorers', [])
    cache.set(cache_key, scorers, SCORERS_CACHE_TTL)
    return scorers[:limit]


def _build_nepali_calendar_context():
    """Today's Nepali (BS) date, a mini month grid, and upcoming holidays for the home dashboard."""
    converter = NepaliDateConverter()
    today = converter.today_nepali_calendar

    weekday_name = NepaliDateConverter.get_weekday_name(today.day_of_week, NameFormat.FULL, NepaliCalendarUtilsLang.ENGLISH)
    month_name = NepaliDateConverter.get_month_name(today.month, NameFormat.FULL, NepaliCalendarUtilsLang.ENGLISH)
    month_label = f'{month_name} {today.year}'

    prev_month = today.month - 1 or 12
    prev_year = today.year if today.month > 1 else today.year - 1
    prev_month_total_days = converter.get_total_days_in_nepali_month(prev_year, prev_month)

    this_year_holidays = {(h.month, h.day): h for h in get_year_holidays(today.year)}

    calendar_days = []
    leading = today.first_day_of_month - 1
    for offset in range(leading, 0, -1):
        calendar_days.append({'day': prev_month_total_days - offset + 1, 'muted': True, 'active': False, 'holiday': None})
    for day in range(1, today.total_days_in_month + 1):
        calendar_days.append({
            'day': day,
            'muted': False,
            'active': day == today.day_of_month,
            'holiday': this_year_holidays.get((today.month, day)),
        })
    trailing = (7 - len(calendar_days) % 7) % 7
    for day in range(1, trailing + 1):
        calendar_days.append({'day': day, 'muted': True, 'active': False, 'holiday': None})

    todays_holiday = this_year_holidays.get((today.month, today.day_of_month))

    upcoming = []
    for bs_year in (today.year, today.year + 1):
        for holiday in get_year_holidays(bs_year):
            try:
                occurs_english = converter.convert_nepali_to_english(bs_year, holiday.month, holiday.day)
            except (ValueError, IndexError):
                continue
            occurs_on = date(occurs_english.year, occurs_english.month, occurs_english.day_of_month)
            if occurs_on > date.today():
                upcoming.append((occurs_on, holiday))
    upcoming.sort(key=lambda item: item[0])

    return {
        'nepali_year': today.year,
        'nepali_month_name': month_name,
        'nepali_day': today.day_of_month,
        'nepali_weekday_name': weekday_name,
        'nepali_month_label': month_label,
        'nepali_calendar_days': calendar_days,
        'nepali_todays_holiday': todays_holiday,
        'nepali_upcoming_holidays': [
            {'name': holiday.name, 'date_label': occurs_on.strftime('%d %b')}
            for occurs_on, holiday in upcoming[:4]
        ],
    }


def _ensure_aware(value):
    """Some upstream APIs (MotoGP pulselive) return timestamps with no UTC offset - assume UTC."""
    return timezone.make_aware(value, dt_timezone.utc) if timezone.is_naive(value) else value


def _relative_time_label(when, now):
    """Human label like 'starts in 2 hours' (future) or '3 days ago' (past) for a datetime vs now."""
    when, now = _ensure_aware(when), _ensure_aware(now)
    delta = (when - now).total_seconds()
    future = delta >= 0
    seconds = abs(delta)
    if seconds < 60:
        value, unit = max(1, int(seconds)), 'second'
    elif seconds < 3600:
        value, unit = int(seconds // 60), 'minute'
    elif seconds < 86400:
        value, unit = int(seconds // 3600), 'hour'
    else:
        value, unit = int(seconds // 86400), 'day'
    unit = unit if value == 1 else f'{unit}s'
    return f'starts in {value} {unit}' if future else f'{value} {unit} ago'


def _build_sports_events_context():
    """Next fixture + latest result across F1, MotoGP and football (PL/CL) for the home sidebar."""
    now = timezone.now()
    events = []

    try:
        meetings = get_f1_meetings(now.year) + get_f1_meetings(now.year + 1)
        upcoming_meetings = sorted((m for m in meetings if m['date_end'] >= now), key=lambda m: m['date_start'])
        if upcoming_meetings:
            next_meeting = upcoming_meetings[0]
            sessions = get_f1_sessions(next_meeting['meeting_key'])
            race_session = next((s for s in sessions if s.get('session_name') == 'Race'), None)
            race_time = _ensure_aware(race_session['date_start'] if race_session else next_meeting['date_start'])
            events.append({
                'when': race_time,
                'is_result': False,
                'text': f"F1 \u2022 {next_meeting['meeting_name']} {_relative_time_label(race_time, now)}",
            })
        past_races = get_f1_past_races(now.year)
        if past_races:
            last_race = past_races[-1]
            last_race_time = _ensure_aware(last_race['date_start'])
            winner = last_race['winner']['name'] if last_race.get('winner') else 'TBC'
            events.append({
                'when': last_race_time,
                'is_result': True,
                'text': f"F1 \u2022 {last_race['meeting_name']} \u2014 {winner} won ({_relative_time_label(last_race_time, now)})",
            })
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('Home sidebar F1 events fetch failed: %s', exc)

    try:
        season_id, _year = get_motogp_season()
        category_id = get_motogp_category_id(season_id)
        motogp_events = get_motogp_events(season_id)
        upcoming_events = [e for e in motogp_events if e['status'] != 'FINISHED']
        if upcoming_events:
            next_event = upcoming_events[0]
            sessions = get_motogp_event_sessions(next_event['id'], category_id)
            race_session = next((s for s in sessions if s.get('type') == 'RAC'), None)
            race_time = _ensure_aware(race_session['date'] if race_session else next_event['date_start'])
            events.append({
                'when': race_time,
                'is_result': False,
                'text': f"MotoGP \u2022 {next_event['name']} {_relative_time_label(race_time, now)}",
            })
        past_races = get_motogp_past_races(season_id, category_id)
        if past_races:
            last_race = past_races[-1]
            last_race_time = _ensure_aware(last_race['date_start'])
            winner = last_race['winner']['name'] if last_race.get('winner') else 'TBC'
            events.append({
                'when': last_race_time,
                'is_result': True,
                'text': f"MotoGP \u2022 {last_race['name']} \u2014 {winner} won ({_relative_time_label(last_race_time, now)})",
            })
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('Home sidebar MotoGP events fetch failed: %s', exc)

    try:
        upcoming_matches = []
        for code in (FOOTBALL_DATA_PL_CODE, FOOTBALL_DATA_CL_CODE):
            upcoming_matches += get_competition_matches(code, 'SCHEDULED')
        upcoming_matches.sort(key=lambda m: m['kickoff'])
        if upcoming_matches:
            match = upcoming_matches[0]
            home_name = match['homeTeam'].get('shortName') or match['homeTeam'].get('name')
            away_name = match['awayTeam'].get('shortName') or match['awayTeam'].get('name')
            events.append({
                'when': match['kickoff'],
                'is_result': False,
                'text': f"Football \u2022 {home_name} vs {away_name} {_relative_time_label(match['kickoff'], now)}",
            })
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('Home sidebar football fixtures fetch failed: %s', exc)

    try:
        finished_matches = []
        for code in (FOOTBALL_DATA_PL_CODE, FOOTBALL_DATA_CL_CODE):
            finished_matches += get_competition_matches(code, 'FINISHED')
        finished_matches.sort(key=lambda m: m['kickoff'], reverse=True)
        if finished_matches:
            match = finished_matches[0]
            home_name = match['homeTeam'].get('shortName') or match['homeTeam'].get('name')
            away_name = match['awayTeam'].get('shortName') or match['awayTeam'].get('name')
            score = match.get('score', {}).get('fullTime', {})
            events.append({
                'when': match['kickoff'],
                'is_result': True,
                'text': (
                    f"Football \u2022 {home_name} {score.get('home')}-{score.get('away')} {away_name} "
                    f"({_relative_time_label(match['kickoff'], now)})"
                ),
            })
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('Home sidebar football results fetch failed: %s', exc)

    upcoming = sorted((e for e in events if not e['is_result']), key=lambda e: e['when'])
    recent = sorted((e for e in events if e['is_result']), key=lambda e: e['when'], reverse=True)
    return {'sports_events': (upcoming + recent)[:6]}


def home(request):
    context = _build_nepali_calendar_context()
    context.update(_build_sports_events_context())

    try:
        context['nepse_summary'] = get_nepse_market_summary()
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('Home NEPSE market summary fetch failed: %s', exc)
        context['nepse_summary'] = None

    # F1/MotoGP context keys are prefixed since both dashboard cards render into the same
    # Dashboard.html template context (unlike their dedicated pages, which never collide).
    context.update({f'f1_{key}': value for key, value in _build_f1_context().items()})
    context.update({f'motogp_{key}': value for key, value in _build_motogp_context().items()})
    context.update(_build_league_context())

    return render(request, 'body/Dashboard/Dashboard.html', context)

def _build_league_context():
    context = {
        'standings': [],
        'top_scorers': [],
        'upcoming_matches': [],
        'next_matches': [],
        'recent_results': [],
        'leader_lead': None,
        'cl_standings': [],
        'cl_top_scorers': [],
        'cl_upcoming_matches': [],
        'cl_recent_results': [],
        'cl_leader_lead': None,
    }
    try:
        context['standings'] = get_competition_standings(FOOTBALL_DATA_PL_CODE)
        if len(context['standings']) > 1:
            context['leader_lead'] = context['standings'][0]['points'] - context['standings'][1]['points']
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('football-data.org standings fetch failed: %s', exc)

    try:
        context['top_scorers'] = get_competition_scorers(FOOTBALL_DATA_PL_CODE, limit=5)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('football-data.org scorers fetch failed: %s', exc)

    try:
        upcoming = sorted(get_competition_matches(FOOTBALL_DATA_PL_CODE, 'SCHEDULED'), key=lambda m: m['kickoff'])
        context['upcoming_matches'] = upcoming[:8]
        context['next_matches'] = upcoming[:2]
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('football-data.org scheduled matches fetch failed: %s', exc)

    try:
        finished = sorted(get_competition_matches(FOOTBALL_DATA_PL_CODE, 'FINISHED'), key=lambda m: m['kickoff'], reverse=True)
        context['recent_results'] = finished[:5]
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('football-data.org finished matches fetch failed: %s', exc)

    try:
        cl_upcoming = sorted(get_competition_matches(FOOTBALL_DATA_CL_CODE, 'SCHEDULED'), key=lambda m: m['kickoff'])
        context['cl_upcoming_matches'] = cl_upcoming[:8]
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('football-data.org Champions League scheduled matches fetch failed: %s', exc)

    try:
        cl_finished = sorted(get_competition_matches(FOOTBALL_DATA_CL_CODE, 'FINISHED'), key=lambda m: m['kickoff'], reverse=True)
        context['cl_recent_results'] = cl_finished[:5]
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('football-data.org Champions League finished matches fetch failed: %s', exc)

    try:
        context['cl_standings'] = get_competition_standings(FOOTBALL_DATA_CL_CODE)
        if len(context['cl_standings']) > 1:
            context['cl_leader_lead'] = context['cl_standings'][0]['points'] - context['cl_standings'][1]['points']
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('football-data.org Champions League standings fetch failed: %s', exc)

    try:
        context['cl_top_scorers'] = get_competition_scorers(FOOTBALL_DATA_CL_CODE, limit=5)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('football-data.org Champions League scorers fetch failed: %s', exc)

    return context


def league(request):
    context = _build_league_context()
    return render(request, 'body/pages/premierleague/PremierLeague.html', context)


def _build_motogp_context():
    context = {
        'next_event': None,
        'next_race_session': None,
        'next_quali_session': None,
        'upcoming_races': [],
        'driver_standings': [],
        'team_standings': [],
        'leader_lead': None,
        'past_races': [],
    }
    try:
        season_id, year = get_motogp_season()
        category_id = get_motogp_category_id(season_id)
        events = get_motogp_events(season_id)
        upcoming = [e for e in events if e['status'] != 'FINISHED']
        context['upcoming_races'] = upcoming
        if upcoming:
            next_event = upcoming[0]
            context['next_event'] = next_event
            sessions = get_motogp_event_sessions(next_event['id'], category_id)
            context['next_race_session'] = next((s for s in sessions if s.get('type') == 'RAC'), None)
            context['next_quali_session'] = next(
                (s for s in sorted(sessions, key=lambda s: s['date'], reverse=True) if s.get('type') == 'Q'), None
            )

        past_races = get_motogp_past_races(season_id, category_id)
        context['past_races'] = past_races

        driver_standings, team_standings = get_motogp_standings(season_id, category_id)
        starts = get_motogp_driver_starts(past_races)
        for row in driver_standings:
            row['starts'] = starts.get(row['rider_id'], 0)
        context['driver_standings'] = driver_standings
        context['team_standings'] = team_standings
        if len(driver_standings) > 1:
            context['leader_lead'] = driver_standings[0]['points'] - driver_standings[1]['points']
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('MotoGP pulselive fetch failed: %s', exc)

    return context


def motogp(request):
    context = _build_motogp_context()
    return render(request, 'body/pages/motogp/motodash.html', context)


def _build_f1_context():
    context = {
        'next_meeting': None,
        'next_race_session': None,
        'next_quali_session': None,
        'upcoming_races': [],
        'driver_standings': [],
        'team_standings': [],
        'leader_lead': None,
        'past_races': [],
    }
    try:
        now = timezone.now()
        meetings = get_f1_meetings(now.year) + get_f1_meetings(now.year + 1)
        upcoming = sorted((m for m in meetings if m['date_end'] >= now), key=lambda m: m['date_start'])
        context['upcoming_races'] = upcoming
        if upcoming:
            next_meeting = upcoming[0]
            context['next_meeting'] = next_meeting
            sessions = get_f1_sessions(next_meeting['meeting_key'])
            context['next_race_session'] = next((s for s in sessions if s.get('session_name') == 'Race'), None)
            context['next_quali_session'] = next((s for s in sessions if s.get('session_name') == 'Qualifying'), None)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('OpenF1 meetings/sessions fetch failed: %s', exc)

    try:
        driver_standings, team_standings = get_f1_standings()
        context['driver_standings'] = driver_standings
        context['team_standings'] = team_standings
        if len(driver_standings) > 1:
            context['leader_lead'] = driver_standings[0]['points'] - driver_standings[1]['points']
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('OpenF1 standings fetch failed: %s', exc)

    try:
        context['past_races'] = get_f1_past_races(timezone.now().year)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error('OpenF1 past races fetch failed: %s', exc)

    return context


def formula1(request):
    context = _build_f1_context()
    return render(request, 'body/pages/formula1/f1_home.html', context)


class ExpenseTrackingView(View):
    template_name = 'body/pages/expense_tracking/expensetracking_dash.html'

    @staticmethod
    def format_expense_date(value):
        if not hasattr(value, 'strftime'):
            return str(value)
        return '{} {}'.format(value.strftime('%b'), value.day)

    def format_expense_rows(self, queryset):
        rows = []
        for expense in queryset:
            slug = expense.category.slug if expense.category else None
            style = CATEGORY_STYLES.get(slug, DEFAULT_CATEGORY_STYLE)
            rows.append({
                'name': expense.name,
                'category_name': expense.category.name if expense.category else 'Uncategorized',
                'chip_class': style['chip'],
                'amount': float(expense.amount),
                'date': self.format_expense_date(expense.date),
            })
        return rows

    def get_available_months(self):
        months = list(
            Expense.objects.annotate(month=TruncMonth('date'))
            .values_list('month', flat=True)
            .distinct()
            .order_by('-month')
        )
        today_month = date.today().replace(day=1)
        if today_month not in months:
            months.insert(0, today_month)
            months.sort(reverse=True)
        return [
            {'value': m.strftime('%Y-%m'), 'label': m.strftime('%B %Y')}
            for m in months
        ]

    def compute_stats(self):
        today = date.today()

        expenses = Expense.objects.select_related('category').all()
        month_expenses = expenses.filter(date__year=today.year, date__month=today.month).all()

        spent_so_far = month_expenses.aggregate(total=Sum('amount'))['total'] or 0
        budget = Budget.objects.filter(month__year=today.year, month__month=today.month).first()
        income_this_month = Income.objects.filter(
            date__year=today.year, date__month=today.month
        ).aggregate(total=Sum('amount'))['total'] or 0
        budget_amount = (budget.amount if budget else 0) + income_this_month
        remaining = budget_amount - spent_so_far
        budget_used_percent = int(min(100, max(0, (spent_so_far / budget_amount * 100)))) if budget_amount else 0
        savings_goal_percent = max(0, 100 - budget_used_percent) if budget_amount else 0

        expense_rows = []
        for expense in expenses:
            slug = expense.category.slug if expense.category else None
            style = CATEGORY_STYLES.get(slug, DEFAULT_CATEGORY_STYLE)
            expense_rows.append({
                'name': expense.name,
                'category_name': expense.category.name if expense.category else 'Uncategorized',
                'chip_class': style['chip'],
                'amount': expense.amount,
                'date': expense.date,
            })

        category_totals = (
            month_expenses.values('category__name', 'category__slug')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )
        distribution = []
        if spent_so_far:
            for row in category_totals[:4]:
                style = CATEGORY_STYLES.get(row['category__slug'], DEFAULT_CATEGORY_STYLE)
                distribution.append({
                    'name': row['category__name'] or 'Uncategorized',
                    'legend_class': style['legend'],
                    'percent': round(row['total'] / spent_so_far * 100),
                })

        return {
            'expenses': expense_rows,
            'budget_amount': budget_amount,
            'spent_so_far': spent_so_far,
            'remaining': remaining,
            'budget_used_percent': budget_used_percent,
            'savings_goal_percent': savings_goal_percent,
            'distribution': distribution,
        }

    def get_context(self, expense_form=None, income_form=None):
        context = {
            'expense_form': expense_form or ExpenseForm(),
            'income_form': income_form or IncomeForm(),
            'converter_form': CurrencyConverterForm(),
            'money_to_get_form': MoneyToGetForm(),
            'money_to_pay_form': MoneyToPayForm(),
            'nepal_add_form': NepalSavingsAddForm(),
            'nepal_use_form': NepalSavingsUseForm(),
            'available_months': self.get_available_months(),
            'current_month_label': date.today().strftime('%B %Y'),
            'money_to_get_entries': MoneyToGet.objects.all(),
            'money_to_get_total': MoneyToGet.objects.aggregate(total=Sum('amount'))['total'] or 0,
            'money_to_pay_entries': MoneyToPay.objects.all(),
            'money_to_pay_total': MoneyToPay.objects.aggregate(total=Sum('amount'))['total'] or 0,
            'nepal_transactions': NepalSavingsTransaction.objects.all(),
            'nepal_total': self.compute_nepal_savings_total(),
        }
        context.update(self.compute_stats())
        return context

    def compute_nepal_savings_total(self):
        totals = NepalSavingsTransaction.objects.aggregate(
            added=Sum('amount', filter=Q(type=NepalSavingsTransaction.ADDED)),
            used=Sum('amount', filter=Q(type=NepalSavingsTransaction.USED)),
        )
        return (totals['added'] or 0) - (totals['used'] or 0)

    @staticmethod
    def is_ajax(request):
        return request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def month_json(self, month_param):
        if not month_param or month_param == 'all':
            rows = self.format_expense_rows(
                Expense.objects.select_related('category').all()
            )
            return JsonResponse({
                'success': True,
                'expenses': rows,
                'month_label': 'All months',
                'has_data': bool(rows),
            })

        try:
            year_str, month_str = month_param.split('-')
            year, month = int(year_str), int(month_str)
            month_label = date(year, month, 1).strftime('%B %Y')
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'Invalid month.'}, status=400)

        queryset = (
            Expense.objects.select_related('category')
            .filter(date__year=year, date__month=month)
            .order_by('-date', '-created_at')
        )
        rows = self.format_expense_rows(queryset)
        return JsonResponse({
            'success': True,
            'expenses': rows,
            'month_label': month_label,
            'has_data': bool(rows),
        })

    def get(self, request):
        if self.is_ajax(request) and 'month' in request.GET:
            return self.month_json(request.GET.get('month'))
        return render(request, self.template_name, self.get_context())

    def stats_json(self, extra=None):
        stats = self.compute_stats()
        data = {
            'budget_amount': float(stats['budget_amount']),
            'spent_so_far': float(stats['spent_so_far']),
            'remaining': float(stats['remaining']),
            'budget_used_percent': stats['budget_used_percent'],
            'savings_goal_percent': stats['savings_goal_percent'],
            'distribution': stats['distribution'],
            'expenses': [
                {
                    'name': row['name'],
                    'category_name': row['category_name'],
                    'chip_class': row['chip_class'],
                    'amount': float(row['amount']),
                    'date': self.format_expense_date(row['date']),
                }
                for row in stats['expenses']
            ],
        }
        if extra:
            data.update(extra)
        return data

    def post(self, request):
        ajax = self.is_ajax(request)
        expense_form = ExpenseForm()
        income_form = IncomeForm()

        if 'expense_submit' in request.POST:
            expense_form = ExpenseForm(request.POST)
            if expense_form.is_valid():
                expense_form.save()
                if ajax:
                    return JsonResponse(self.stats_json({
                        'success': True,
                        'message': 'Expense added successfully.',
                    }))
                messages.success(request, 'Expense added successfully.')
                return redirect('expensetrackingpage')
            if ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Please fix the errors in the expense form.',
                    'errors': {field: [str(e) for e in errs] for field, errs in expense_form.errors.items()},
                }, status=400)
            messages.error(request, 'Please fix the errors in the expense form.')
        elif 'income_submit' in request.POST:
            income_form = IncomeForm(request.POST)
            if income_form.is_valid():
                income_form.save()
                if ajax:
                    return JsonResponse(self.stats_json({
                        'success': True,
                        'message': 'Income added successfully.',
                    }))
                messages.success(request, 'Income added successfully.')
                return redirect('expensetrackingpage')
            if ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Please fix the errors in the income form.',
                    'errors': {field: [str(e) for e in errs] for field, errs in income_form.errors.items()},
                }, status=400)
            messages.error(request, 'Please fix the errors in the income form.')

        return render(request, self.template_name, self.get_context(expense_form, income_form))


def money_to_pay_json(extra=None):
    entries = MoneyToPay.objects.all()
    data = {
        'entries': [
            {'id': entry.id, 'name': entry.name, 'amount': float(entry.amount)}
            for entry in entries
        ],
        'total': float(entries.aggregate(total=Sum('amount'))['total'] or 0),
    }
    if extra:
        data.update(extra)
    return data


def nepal_savings_json(extra=None):
    transactions = NepalSavingsTransaction.objects.all()
    data = {
        'transactions': [
            {
                'id': tx.id,
                'type': tx.type,
                'amount': float(tx.amount),
                'note': tx.note,
                'date': tx.date.isoformat(),
            }
            for tx in transactions
        ],
        'total': float(
            (
                transactions.filter(type=NepalSavingsTransaction.ADDED).aggregate(total=Sum('amount'))['total'] or 0
            ) - (
                transactions.filter(type=NepalSavingsTransaction.USED).aggregate(total=Sum('amount'))['total'] or 0
            )
        ),
    }
    if extra:
        data.update(extra)
    return data


@require_POST
def nepal_savings_update(request, pk):
    transaction = get_object_or_404(NepalSavingsTransaction, pk=pk)
    form = NepalSavingsAddForm(request.POST, instance=transaction)
    if form.is_valid():
        tx = form.save(commit=False)
        tx.type = transaction.type
        tx.date = transaction.date
        tx.save()
        return JsonResponse(nepal_savings_json({'success': True, 'message': 'Transaction updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def nepal_savings_delete(request, pk):
    transaction = get_object_or_404(NepalSavingsTransaction, pk=pk)
    transaction.delete()
    return JsonResponse(nepal_savings_json({'success': True, 'message': 'Transaction deleted.'}))


@require_POST
def nepal_savings_add(request):
    form = NepalSavingsAddForm(request.POST)
    if form.is_valid():
        tx = form.save(commit=False)
        tx.type = NepalSavingsTransaction.ADDED
        tx.date = date.today()
        tx.save()
        return JsonResponse(nepal_savings_json({'success': True, 'message': 'Savings added.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def nepal_savings_use(request):
    form = NepalSavingsUseForm(request.POST)
    if form.is_valid():
        tx = form.save(commit=False)
        tx.type = NepalSavingsTransaction.USED
        tx.date = date.today()
        tx.save()
        return JsonResponse(nepal_savings_json({'success': True, 'message': 'Money used.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


def money_to_get_json(extra=None):
    entries = MoneyToGet.objects.all()
    data = {
        'entries': [
            {'id': entry.id, 'name': entry.name, 'amount': float(entry.amount)}
            for entry in entries
        ],
        'total': float(entries.aggregate(total=Sum('amount'))['total'] or 0),
    }
    if extra:
        data.update(extra)
    return data


@require_POST
def money_to_get_add(request):
    form = MoneyToGetForm(request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse(money_to_get_json({'success': True, 'message': 'Entry added.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def money_to_get_update(request, pk):
    entry = get_object_or_404(MoneyToGet, pk=pk)
    form = MoneyToGetForm(request.POST, instance=entry)
    if form.is_valid():
        form.save()
        return JsonResponse(money_to_get_json({'success': True, 'message': 'Entry updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def money_to_get_delete(request, pk):
    entry = get_object_or_404(MoneyToGet, pk=pk)
    entry.delete()
    return JsonResponse(money_to_get_json({'success': True, 'message': 'Entry removed.'}))


@require_POST
def money_to_pay_add(request):
    form = MoneyToPayForm(request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse(money_to_pay_json({'success': True, 'message': 'Entry added.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def money_to_pay_update(request, pk):
    entry = get_object_or_404(MoneyToPay, pk=pk)
    form = MoneyToPayForm(request.POST, instance=entry)
    if form.is_valid():
        form.save()
        return JsonResponse(money_to_pay_json({'success': True, 'message': 'Entry updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def money_to_pay_delete(request, pk):
    entry = get_object_or_404(MoneyToPay, pk=pk)
    entry.delete()
    return JsonResponse(money_to_pay_json({'success': True, 'message': 'Entry removed.'}))


def stockex(request):
    context = portfolio_json()
    context.update(price_alerts_json())
    context.update(watchlist_json())
    ws_scheme = 'wss' if request.is_secure() else 'ws'
    context['nepse_ws_url'] = f"{ws_scheme}://{settings.NEPSE_WS_HOST}"
    return render(request, 'body/pages/stockex/stockex_dash.html', context)


def _format_nepali_amount(value):
    """Format a raw Rs amount using Lakh/Crore/Arba/Kharba units."""
    value = float(value or 0)
    if value >= 1e11:
        return f"Rs {value / 1e11:.2f} Kharba"
    if value >= 1e9:
        return f"Rs {value / 1e9:.2f} Arba"
    if value >= 1e7:
        return f"Rs {value / 1e7:.2f} Crore"
    if value >= 1e5:
        return f"Rs {value / 1e5:.2f} Lakh"
    return f"Rs {value:,.2f}"


PORTFOLIO_PRICE_CACHE_KEY = 'nepse_price_volume_map'
PORTFOLIO_PRICE_CACHE_TTL = 60  # NEPSE prices tick constantly; keep this short


def get_nepse_price_map():
    """Symbol -> {name, price, change_percent, volume} from the LAN NEPSE PriceVolume feed, cached briefly."""
    price_map = cache.get(PORTFOLIO_PRICE_CACHE_KEY)
    if price_map is not None:
        return price_map

    response = requests.get(f"{NEPSE_API_BASE}/PriceVolume", timeout=5)
    response.raise_for_status()
    price_map = {
        row["symbol"]: {
            "name": (row.get("securityName") or "").strip(),
            "price": row.get("lastTradedPrice"),
            "change_percent": row.get("percentageChange"),
            "volume": row.get("totalTradeQuantity"),
        }
        for row in response.json()
        if row.get("symbol")
    }
    cache.set(PORTFOLIO_PRICE_CACHE_KEY, price_map, PORTFOLIO_PRICE_CACHE_TTL)
    return price_map


NEPSE_HOME_SUMMARY_CACHE_KEY = 'nepse_home_summary'
NEPSE_HOME_SUMMARY_CACHE_TTL = 60  # matches PORTFOLIO_PRICE_CACHE_TTL - NEPSE prices tick constantly


def get_nepse_market_summary():
    """Index value/change, turnover, market cap, advance/decline, top gainer/loser for the home page tile."""
    summary = cache.get(NEPSE_HOME_SUMMARY_CACHE_KEY)
    if summary is not None:
        return summary

    index_data = requests.get(f"{NEPSE_API_BASE}/NepseIndex", timeout=5).json()
    summary_data = requests.get(f"{NEPSE_API_BASE}/Summary", timeout=5).json()
    gainers_data = requests.get(f"{NEPSE_API_BASE}/TopGainers", timeout=5).json()
    losers_data = requests.get(f"{NEPSE_API_BASE}/TopLosers", timeout=5).json()

    nepse_index = index_data.get("NEPSE Index", {})
    price_map = get_nepse_price_map()
    advances = sum(1 for row in price_map.values() if (row.get("change_percent") or 0) > 0)
    declines = sum(1 for row in price_map.values() if (row.get("change_percent") or 0) < 0)
    unchanged = len(price_map) - advances - declines

    summary = {
        "index_value": nepse_index.get("currentValue"),
        "index_change": nepse_index.get("change"),
        "index_change_percent": nepse_index.get("perChange"),
        "turnover": _format_nepali_amount(summary_data.get("Total Turnover Rs:")),
        "traded_shares": summary_data.get("Total Traded Shares"),
        "transactions": summary_data.get("Total Transactions"),
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "gainers": [
            {
                "symbol": g["symbol"],
                "company": g.get("securityName"),
                "price": g.get("ltp"),
                "change_percent": g.get("percentageChange"),
            }
            for g in gainers_data[:3]
        ],
        "losers": [
            {
                "symbol": l["symbol"],
                "company": l.get("securityName"),
                "price": l.get("ltp"),
                "change_percent": l.get("percentageChange"),
            }
            for l in losers_data[:3]
        ],
    }
    cache.set(NEPSE_HOME_SUMMARY_CACHE_KEY, summary, NEPSE_HOME_SUMMARY_CACHE_TTL)
    return summary


def get_watchlist_symbols():
    """Every active equity in our watched sectors, symbol -> {company, category}, sourced from /CompanyList."""
    companies = cache.get(COMPANY_LIST_CACHE_KEY)
    if companies is None:
        response = requests.get(f"{NEPSE_API_BASE}/CompanyList", timeout=5)
        response.raise_for_status()
        companies = response.json()
        cache.set(COMPANY_LIST_CACHE_KEY, companies, COMPANY_LIST_CACHE_TTL)

    symbols = {}
    for row in companies:
        sector = row.get("sectorName")
        category = WATCHLIST_SECTOR_CATEGORIES.get(sector)
        expected_instrument_type = WATCHLIST_SECTOR_INSTRUMENT_TYPE.get(sector, "Equity")
        if not category or row.get("status") != "A" or row.get("instrumentType") != expected_instrument_type:
            continue
        symbol = row.get("symbol")
        if not symbol or symbol in symbols:
            continue
        symbols[symbol] = {
            "company": (row.get("companyName") or row.get("securityName") or "").strip(),
            "category": category,
        }
    return symbols


def _watchlist_sparkline(symbol, change_percent):
    """Deterministic pseudo 7D trend line (no historical feed available), seeded per symbol."""
    rng = random.Random(symbol)
    trending_up = (change_percent or 0) >= 0
    value = 15.0
    points = [value]
    for _ in range(10):
        drift = rng.uniform(0.5, 2.5) * (1 if trending_up else -1)
        value = max(2.0, value + drift + rng.uniform(-1, 1))
        points.append(round(value, 1))
    return ",".join(str(p) for p in points)


def watchlist_json():
    """Watchlist rows (with live price/change/volume) plus the distinct category list."""
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        price_map = {}
    try:
        watchlist_symbols = get_watchlist_symbols()
    except (requests.RequestException, ValueError):
        watchlist_symbols = {}

    rows = []
    categories = []
    for symbol, meta in watchlist_symbols.items():
        info = price_map.get(symbol)
        change_percent = info["change_percent"] if info else None
        rows.append({
            "symbol": symbol,
            "company": meta["company"],
            "category": meta["category"],
            "price": info["price"] if info else None,
            "change_percent": change_percent,
            "volume": info["volume"] if info else None,
            "sparkline": _watchlist_sparkline(symbol, change_percent),
        })
        if meta["category"] not in categories:
            categories.append(meta["category"])

    return {"watchlist": rows, "watchlist_categories": categories}


def portfolio_symbols(request):
    """List of tradable symbols/names/prices for the 'select stock' dropdown on the portfolio modal."""
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        return JsonResponse({"error": "NEPSE API is unreachable"}, status=502)

    symbols = [
        {"symbol": symbol, "name": info["name"], "price": info["price"]}
        for symbol, info in sorted(price_map.items())
    ]
    return JsonResponse({"symbols": symbols})


def portfolio_json(extra=None):
    """Holdings + totals payload shared by the page render and every portfolio CRUD response."""
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        price_map = {}

    rows = []
    total_invested = 0.0
    total_current = 0.0
    for holding in PortfolioHolding.objects.all():
        info = price_map.get(holding.symbol)
        current_price = float(info["price"]) if info and info.get("price") is not None else float(holding.buy_price)
        invested = float(holding.buy_price) * holding.quantity
        current_value = current_price * holding.quantity
        profit = current_value - invested
        profit_percent = (profit / invested * 100) if invested else 0.0
        total_invested += invested
        total_current += current_value
        rows.append({
            "id": holding.id,
            "symbol": holding.symbol,
            "company_name": holding.company_name or (info["name"] if info else ""),
            "quantity": holding.quantity,
            "buy_price": float(holding.buy_price),
            "current_price": current_price,
            "buy_date": holding.buy_date.isoformat(),
            "invested": invested,
            "current_value": current_value,
            "profit": profit,
            "profit_percent": profit_percent,
            "is_up": profit >= 0,
        })

    total_profit = total_current - total_invested
    total_profit_percent = (total_profit / total_invested * 100) if total_invested else 0.0
    data = {
        "holdings": rows,
        "total_invested": total_invested,
        "total_current": total_current,
        "total_profit": total_profit,
        "total_profit_percent": total_profit_percent,
    }
    if extra:
        data.update(extra)
    return data


@require_POST
def portfolio_add(request):
    form = PortfolioHoldingForm(request.POST)
    if form.is_valid():
        holding = form.save(commit=False)
        if not holding.company_name:
            try:
                info = get_nepse_price_map().get(holding.symbol)
                if info:
                    holding.company_name = info["name"]
            except (requests.RequestException, ValueError):
                pass
        holding.save()
        return JsonResponse(portfolio_json({'success': True, 'message': 'Holding added.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def portfolio_update(request, pk):
    holding = get_object_or_404(PortfolioHolding, pk=pk)
    form = PortfolioHoldingForm(request.POST, instance=holding)
    if form.is_valid():
        form.save()
        return JsonResponse(portfolio_json({'success': True, 'message': 'Holding updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def portfolio_delete(request, pk):
    holding = get_object_or_404(PortfolioHolding, pk=pk)
    holding.delete()
    return JsonResponse(portfolio_json({'success': True, 'message': 'Holding removed.'}))


def _price_alert_status(alert, current_price):
    """Row payload for a single alert, including its live current price and status text."""
    target = float(alert.target_price)
    action_label = "Buy" if alert.action == PriceAlert.BUY else "Sell"
    if alert.is_triggered:
        if alert.triggered_direction == PriceAlert.UP:
            status_text = f"{action_label} signal — crossed above Rs {target:,.2f}"
        else:
            status_text = f"{action_label} signal — dropped below Rs {target:,.2f}"
    else:
        status_text = f"{action_label} alert — notify when price hits Rs {target:,.2f}"
    return {
        "id": alert.id,
        "symbol": alert.symbol,
        "company_name": alert.company_name,
        "action": alert.action,
        "action_display": action_label,
        "target_price": target,
        "current_price": current_price,
        "is_triggered": alert.is_triggered,
        "direction": alert.triggered_direction,
        "status_text": status_text,
        "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
    }


def price_alerts_json(extra=None):
    """Alerts list + active count payload shared by the page render and every alert CRUD response."""
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        price_map = {}

    rows = []
    active_count = 0
    for alert in PriceAlert.objects.all():
        info = price_map.get(alert.symbol)
        current_price = float(info["price"]) if info and info.get("price") is not None else float(alert.last_price or alert.target_price)
        if not alert.is_triggered:
            active_count += 1
        rows.append(_price_alert_status(alert, current_price))

    data = {"price_alerts": rows, "price_alerts_active_count": active_count}
    if extra:
        data.update(extra)
    return data


@require_POST
def price_alert_add(request):
    form = PriceAlertForm(request.POST)
    if form.is_valid():
        alert = form.save(commit=False)
        try:
            info = get_nepse_price_map().get(alert.symbol)
        except (requests.RequestException, ValueError):
            info = None
        if info:
            alert.last_price = info["price"]
            if not alert.company_name:
                alert.company_name = info["name"]
        alert.save()
        return JsonResponse(price_alerts_json({'success': True, 'message': 'Alert created.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def price_alert_update(request, pk):
    alert = get_object_or_404(PriceAlert, pk=pk)
    form = PriceAlertForm(request.POST, instance=alert)
    if form.is_valid():
        alert = form.save(commit=False)
        # Editing re-arms the alert with a fresh baseline price.
        alert.is_triggered = False
        alert.triggered_direction = ""
        alert.triggered_at = None
        try:
            info = get_nepse_price_map().get(alert.symbol)
        except (requests.RequestException, ValueError):
            info = None
        alert.last_price = info["price"] if info else None
        alert.save()
        return JsonResponse(price_alerts_json({'success': True, 'message': 'Alert updated.'}))
    return JsonResponse({
        'success': False,
        'message': 'Please fix the errors below.',
        'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
    }, status=400)


@require_POST
def price_alert_delete(request, pk):
    alert = get_object_or_404(PriceAlert, pk=pk)
    alert.delete()
    return JsonResponse(price_alerts_json({'success': True, 'message': 'Alert removed.'}))


def evaluate_price_alerts():
    """Check untriggered PriceAlerts against live prices, flip+WhatsApp any that just crossed target.

    Shared by the dashboard's poll endpoint (price_alerts_check) and the check_price_alerts
    management command, so a triggered alert is only ever messaged once regardless of which
    caller notices it first (the DB's is_triggered flag is the single source of truth).
    Returns the list of status dicts for alerts that triggered on this call.
    """
    try:
        price_map = get_nepse_price_map()
    except (requests.RequestException, ValueError):
        return []

    triggered_now = []
    for alert in PriceAlert.objects.filter(is_triggered=False):
        info = price_map.get(alert.symbol)
        if not info or info.get("price") is None:
            continue
        current_price = float(info["price"])
        target = float(alert.target_price)
        last_price = float(alert.last_price) if alert.last_price is not None else None

        if last_price is None:
            alert.last_price = current_price
            alert.save(update_fields=["last_price"])
            continue

        crossed_up = last_price < target <= current_price
        crossed_down = last_price > target >= current_price
        if crossed_up or crossed_down:
            alert.is_triggered = True
            alert.triggered_direction = PriceAlert.UP if crossed_up else PriceAlert.DOWN
            alert.triggered_at = timezone.now()
            alert.last_price = current_price
            alert.save()
            status = _price_alert_status(alert, current_price)
            triggered_now.append(status)
            action_word = "BUY" if alert.action == PriceAlert.BUY else "SELL"
            direction_text = "crossed above" if crossed_up else "dropped below"
            send_whatsapp_message(
                f"\U0001F514 {alert.symbol} {action_word} ALERT: price {direction_text} "
                f"Rs {target:,.2f} (now Rs {current_price:,.2f})"
            )
        else:
            alert.last_price = current_price
            alert.save(update_fields=["last_price"])

    return triggered_now


def price_alerts_check(request):
    """Polled by the dashboard: evaluates active alerts and flags any that just crossed their target."""
    triggered_now = evaluate_price_alerts()
    return JsonResponse(price_alerts_json({'triggered': triggered_now}))


def nepse_live_data(request):
    """Proxy live NEPSE data from the Mac mini's REST API for the stock dashboard."""
    try:
        index_data = requests.get(f"{NEPSE_API_BASE}/NepseIndex", timeout=5).json()
        summary_data = requests.get(f"{NEPSE_API_BASE}/Summary", timeout=5).json()
        gainers_data = requests.get(f"{NEPSE_API_BASE}/TopGainers", timeout=5).json()
        losers_data = requests.get(f"{NEPSE_API_BASE}/TopLosers", timeout=5).json()
        price_volume_data = requests.get(f"{NEPSE_API_BASE}/PriceVolume", timeout=5).json()
    except (requests.RequestException, ValueError):
        return JsonResponse({"error": "Mac mini NEPSE API is unreachable"}, status=502)

    nepse_index = index_data.get("NEPSE Index", {})
    advances = sum(1 for s in price_volume_data if s.get("percentageChange", 0) > 0)
    declines = sum(1 for s in price_volume_data if s.get("percentageChange", 0) < 0)
    unchanged = sum(1 for s in price_volume_data if s.get("percentageChange", 0) == 0)

    try:
        watchlist_symbols = get_watchlist_symbols()
    except (requests.RequestException, ValueError):
        watchlist_symbols = {}

    watchlist = [
        {
            "symbol": s["symbol"],
            "price": s["lastTradedPrice"],
            "changePercent": s["percentageChange"],
            "volume": s["totalTradeQuantity"],
        }
        for s in price_volume_data
        if s.get("symbol") in watchlist_symbols
    ]

    data = {
        "index": {
            "value": nepse_index.get("currentValue"),
            "change": nepse_index.get("change"),
            "changePercent": nepse_index.get("perChange"),
            "high": nepse_index.get("high"),
            "low": nepse_index.get("low"),
            "prevClose": nepse_index.get("previousClose"),
        },
        "market": {
            "turnover": _format_nepali_amount(summary_data.get("Total Turnover Rs:")),
            "marketCap": _format_nepali_amount(summary_data.get("Total Market Capitalization Rs:")),
            "advances": advances,
            "declines": declines,
            "unchanged": unchanged,
        },
        "gainers": [
            {"symbol": g["symbol"], "company": g["securityName"], "price": g["ltp"], "changePercent": g["percentageChange"]}
            for g in gainers_data[:5]
        ],
        "losers": [
            {"symbol": l["symbol"], "company": l["securityName"], "price": l["ltp"], "changePercent": l["percentageChange"]}
            for l in losers_data[:5]
        ],
        "watchlist": watchlist,
    }
    return JsonResponse(data)


logger = logging.getLogger(__name__)

# Free-tier exchangerate-api.com keys only allow the /latest/USD endpoint, not
# per-pair conversion, so conversions are computed locally from USD-based rates.
EXCHANGERATE_API_RATES_URL = 'https://v6.exchangerate-api.com/v6/{}/latest/USD'
EXCHANGERATE_API_RATES_CACHE_KEY = 'exchangerate_api_usd_rates'
EXCHANGERATE_API_RATES_CACHE_TTL = 3600  # free plan refreshes rates hourly


def get_usd_rates():
    rates = cache.get(EXCHANGERATE_API_RATES_CACHE_KEY)
    if rates is not None:
        return rates

    response = requests.get(
        EXCHANGERATE_API_RATES_URL.format(settings.EXCHANGERATE_API_KEY),
        timeout=5,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get('result') != 'success':
        raise ValueError('exchangerate-api.com returned an invalid rates response')

    rates = payload['conversion_rates']
    cache.set(EXCHANGERATE_API_RATES_CACHE_KEY, rates, EXCHANGERATE_API_RATES_CACHE_TTL)
    return rates


@require_POST
def convert_currency(request):
    form = CurrencyConverterForm(request.POST)
    if not form.is_valid():
        return JsonResponse({
            'success': False,
            'message': 'Please fix the errors below.',
            'errors': {field: [str(e) for e in errs] for field, errs in form.errors.items()},
        }, status=400)

    if not settings.EXCHANGERATE_API_KEY:
        return JsonResponse({
            'success': False,
            'message': 'Currency conversion is not configured. Missing API key.',
        }, status=500)

    amount = form.cleaned_data['amount']
    from_currency = form.cleaned_data['from_currency']
    to_currency = form.cleaned_data['to_currency']

    try:
        rates = get_usd_rates()
    except (requests.RequestException, ValueError) as exc:
        logger.error('exchangerate-api.com rates fetch failed: %s', exc)
        return JsonResponse({
            'success': False,
            'message': 'Could not reach the currency conversion service. Please try again later.',
        }, status=502)

    if from_currency not in rates or to_currency not in rates:
        return JsonResponse({
            'success': False,
            'message': 'One of the selected currencies is not supported.',
        }, status=400)

    amount_in_usd = float(amount) / rates[from_currency]
    result = amount_in_usd * rates[to_currency]
    return JsonResponse({
        'success': True,
        'amount': float(amount),
        'from_currency': from_currency,
        'to_currency': to_currency,
        'result': result,
        'message': '{:.2f} {} = {:.2f} {}'.format(float(amount), from_currency, result, to_currency),
    })
