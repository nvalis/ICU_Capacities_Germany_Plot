#!/usr/bin/env python
# coding: utf-8

import pandas
import glob
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


data_raw = pandas.DataFrame()
for file_path in glob.glob('./*.json'):
    data_raw = data_raw.append(pandas.read_json(file_path), ignore_index=True)
data = data_raw.copy() # keep raw data
# convert nested description column to str to allow further processing
data.description = data.description.astype('str')
data.last_update = pandas.to_datetime(data.last_update, format='%d.%m.%Y %H:%M')

data_unique = pandas.DataFrame()
clinics = data.name.unique()
for clinic in clinics:
    data_unique = data_unique.append(data[data.name == clinic].drop_duplicates())
data_unique = data_unique.sort_values('last_update')

times = data_unique.last_update.unique()

counts = []
for time in times:
    up_until = data_unique[data_unique.last_update <= time]
    only_newest_status = up_until.drop_duplicates(subset=['name'], keep='last')
    counts_now = {}
    for column in ['status_icu_low_care', 'status_icu_high_care', 'status_ecmo']:
        counts_now[column] = only_newest_status[column].value_counts()
    counts.append(counts_now)

fig, ax = plt.subplots(3, 1, figsize=(10,10))

def subplot(ax, column):
    this_counts = {}
    statuses = ['available', 'limited', 'occupied', 'unavailable']
    for status in statuses:
        this_counts[status] = []
        for c in counts:
            try:
                this_counts[status].append(c[column][status])
            except KeyError:
                this_counts[status].append(0)
    ax.stackplot(
        times,
        this_counts[statuses[0]], this_counts[statuses[1]], this_counts[statuses[2]], this_counts[statuses[3]],
        labels=statuses,
        colors=['#3CA902', '#F6D50E', '#F60E0E', '#ccc']
    )
    ax.set_title(column)
    ax.set_ylabel('Clinics')
    ax.set_xlim(datetime(2020, 3, 17), datetime.now())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y.%m.%d'))
    ax.grid()
    ax.set_axisbelow(True)


subplot(ax[0], 'status_icu_low_care')
subplot(ax[1], 'status_icu_high_care')
subplot(ax[2], 'status_ecmo')
fig.tight_layout()
fig.savefig('plot.png', dpi=300)
