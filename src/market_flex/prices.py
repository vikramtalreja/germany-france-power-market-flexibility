"""Validate ENTSO-E GUI price exports and align the selected 2024 series."""
from pathlib import Path
import numpy as np
import pandas as pd

PRICE = 'Day-ahead Price (EUR/MWh)'

def parse_local(values):
    # Explicit labels disambiguate the repeated autumn hour. Unlabelled
    # ambiguous times and nonexistent spring times fail rather than shift.
    result = []
    for value in values:
        stamp = pd.to_datetime(value.split(' (')[0], format='%d/%m/%Y %H:%M:%S')
        ambiguous = True if '(CEST)' in value else False if '(CET)' in value else 'raise'
        result.append(stamp.tz_localize('Europe/Berlin', ambiguous=ambiguous).tz_convert('UTC'))
    return pd.DatetimeIndex(result)

def load_prices(path, zone, sequence):
    raw = pd.read_csv(path)
    if set(raw['Area']) != {f'BZN|{zone}'}:
        raise ValueError(f'Unexpected bidding zone in {path}')
    data = raw.loc[raw['Sequence'].eq(sequence)].copy()
    if data.empty:
        raise ValueError(f'Missing sequence: {sequence}')
    intervals = data['MTU (CET/CEST)'].str.split(' - ', expand=True)
    start, end = parse_local(intervals[0]), parse_local(intervals[1])
    prices = pd.to_numeric(data[PRICE], errors='raise').to_numpy()
    if not np.isfinite(prices).all():
        raise ValueError('Non-finite prices')
    duration = (end - start).total_seconds() / 3600
    expected_step = 0.25 if zone == 'DE-LU' else 1.0
    if not np.allclose(duration, expected_step):
        raise ValueError('Unexpected interval duration')
    expected = pd.date_range('2024-01-01', '2025-01-01', freq='15min' if zone == 'DE-LU' else 'h', tz='Europe/Berlin', inclusive='left').tz_convert('UTC')
    if not start.equals(expected):
        raise ValueError('Intervals contain gaps, duplicates, disorder or wrong coverage')
    series = pd.Series(prices, index=start, name=zone)
    if zone == 'DE-LU':
        groups = series.resample('h')
        if not groups.count().eq(4).all() or not groups.nunique().eq(1).all():
            raise ValueError('Sequence 1 is not constant across each complete delivery hour')
        series = groups.mean()
    return series

def compare(directory):
    sources = {}
    for path in Path(directory).glob('*.csv'):
        head = pd.read_csv(path, nrows=1)
        if 'Area' in head and len(head):
            zone = head['Area'].iloc[0].removeprefix('BZN|')
            if zone in ('FR', 'DE-LU'):
                if zone in sources:
                    raise ValueError(f'Multiple files for {zone}')
                sources[zone] = path
    frame = pd.concat([load_prices(sources['DE-LU'], 'DE-LU', 'Sequence 1'), load_prices(sources['FR'], 'FR', 'Without Sequence')], axis=1)
    if len(frame) != 8784 or frame.isna().any().any():
        raise ValueError('Incomplete common year')
    frame.index.name = 'timestamp_utc'
    frame['spread_eur_mwh'] = frame['DE-LU'] - frame['FR']
    summary = pd.DataFrame({zone: {'hours':len(frame), 'mean_eur_mwh':frame[zone].mean(), 'minimum_eur_mwh':frame[zone].min(), 'maximum_eur_mwh':frame[zone].max(), 'negative_hours':int(frame[zone].lt(0).sum())} for zone in ('DE-LU','FR')}).T
    return frame, summary
