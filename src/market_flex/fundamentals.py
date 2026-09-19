"""2024 SMARD and RTE actuals. All joins use UTC; missing values stay missing."""
from pathlib import Path
import numpy as np
import pandas as pd

START, END = '2023-12-31T23:00Z', '2024-12-31T23:00Z'
HOURS = pd.date_range(START, END, freq='h', inclusive='left', name='timestamp_utc')
FR_COLUMNS = {
    'Consommation (MW)': 'demand_mw', 'Eolien (MW)': 'wind_mw',
    'Solaire (MW)': 'solar_mw', 'Nucléaire (MW)': 'nuclear_mw',
    'Hydraulique (MW)': 'hydro_mw', 'Gaz (MW)': 'gas_mw',
    'Charbon (MW)': 'coal_mw', 'Fioul (MW)': 'oil_mw',
    'Pompage (MW)': 'pumping_signed_mw', 'Bioénergies (MW)': 'bioenergy_mw',
    'Ech. physiques (MW)': 'physical_exchange_signed_mw',
}

def complete_hourly(frame, samples):
    """Do not treat a partial hour as a complete hourly average."""
    grouped = frame.resample('h')
    return grouped.mean().where(grouped.count().eq(samples)).reindex(HOURS)

def deduplicate_actuals(frame):
    if (frame.groupby(level=0).nunique(dropna=False) > 1).any().any():
        raise ValueError('Conflicting actual values at duplicate timestamps')
    return frame.loc[~frame.index.duplicated(keep='first')].sort_index()

def smard(path):
    raw = pd.read_csv(path, sep=';', thousands=',', na_values=['-'])
    local = pd.DatetimeIndex(pd.to_datetime(raw['Start date'], format='%b %d, %Y %I:%M %p'))
    # Preserve source order to distinguish the two occurrences of the autumn hour.
    index = local.tz_localize('Europe/Berlin', ambiguous='infer', nonexistent='raise').tz_convert('UTC')
    if not index.is_unique or not (index[1:] - index[:-1] == pd.Timedelta('15min')).all():
        raise ValueError('SMARD source has gaps, duplicates or incorrect ordering')
    if not all('[MWh]' in c for c in raw.columns[2:]):
        raise ValueError('Expected MWh-per-quarter-hour SMARD columns')
    values = raw.iloc[:, 2:].apply(pd.to_numeric, errors='raise')
    values.columns = [c.split(' [MWh]')[0] for c in values.columns]
    values.index = index
    expected = pd.date_range(START, END, freq='15min', inclusive='left')
    if not expected.isin(index).all():
        raise ValueError('SMARD does not cover the complete 2024 delivery year')
    # Convert interval energy to average power before aggregating.
    return complete_hourly(values * 4, 4)

def load_germany(generation, consumption):
    g, c = smard(generation), smard(consumption)
    frame = pd.DataFrame(index=HOURS)
    frame['demand_mw'] = c['grid load']
    frame['wind_mw'] = g['Wind offshore'] + g['Wind onshore']
    frame['solar_mw'] = g['Photovoltaics']
    for source, target in [('Nuclear','nuclear_mw'), ('Hydropower','hydro_mw'), ('Fossil gas','gas_mw'), ('Lignite','lignite_mw'), ('Hard coal','coal_mw')]:
        frame[target] = g[source]
    frame['residual_load_mw'] = frame['demand_mw'] - frame['wind_mw'] - frame['solar_mw']
    delta = (frame['residual_load_mw'] - c['Residual load']).abs()
    return frame, {'smard_residual_max_difference_mw': float(delta.max())}

def load_france(path):
    raw = pd.read_csv(path, sep=';', low_memory=False, na_values=['ND','-'])
    stamp = pd.to_datetime(raw['Date et Heure'], utc=True)
    raw = raw.loc[(stamp >= pd.Timestamp(START)) & (stamp < pd.Timestamp(END))].copy()
    if set(raw['Périmètre']) != {'France'}:
        raise ValueError('Expected French national data')
    raw.index = pd.DatetimeIndex(stamp.loc[raw.index])
    data = raw[list(FR_COLUMNS)].apply(pd.to_numeric, errors='raise').rename(columns=FR_COLUMNS)
    # Quarter-hour forecast-only rows are not actual observations.
    actual = data.loc[~data.isna().all(axis=1)]
    before = len(actual)
    actual = deduplicate_actuals(actual)
    expected = pd.date_range(START, END, freq='30min', inclusive='left')
    if not actual.index.isin(expected).all():
        raise ValueError('Actual observations do not lie on the half-hour grid')
    hourly = complete_hourly(actual.reindex(expected), 2)
    hourly['residual_load_mw'] = hourly['demand_mw'] - hourly['wind_mw'] - hourly['solar_mw']
    audit = {'french_duplicate_actual_rows_removed': before-len(actual),
             'french_missing_half_hours_utc': [str(t) for t in expected.difference(actual.index)]}
    return hourly, audit

def analyse(prices, germany, france):
    frames = []
    for zone, data in [('DE-LU',germany), ('FR',france)]:
        f = data.copy()
        f['price_eur_mwh'] = prices[zone].reindex(HOURS)
        f['zone'] = zone
        f['fundamentals_valid'] = f[['demand_mw','wind_mw','solar_mw']].notna().all(axis=1)
        f['quality'] = np.where(f['fundamentals_valid'], 'complete', 'missing_actuals')
        frames.append(f)
    return pd.concat(frames).reset_index()
