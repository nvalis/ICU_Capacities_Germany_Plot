#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import json
import re
import os
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def get_matching_file_names(regex, path="."):
    return sorted([f for f in os.listdir(path) if re.match(regex, f)])


def get_file_names(path="."):
    return get_matching_file_names(r"^.*(?<=_new)\.json$", path=path)


def load_data(path):
    cont = json.load(open(path, encoding="utf8"))
    return pd.json_normalize(cont["data"])  # we only need 'data'


def get_clinic_ids(path):
    dat = load_data(path)
    return dat["id"].sort_values()


file_names = get_file_names()
scrape_times = [
    datetime.strptime(Path(p).stem, "%y%m%d_%H%M%S_new") for p in file_names
]
print(f"Found {len(file_names)} data files")
clinics = get_clinic_ids(file_names[-1])
print(f"Last state contains {len(clinics)} clinics")


raw_data = pd.DataFrame()
for fn in file_names:
    raw_data = raw_data.append(load_data(fn), ignore_index=True)
raw_data.meldezeitpunkt = pd.to_datetime(raw_data.meldezeitpunkt)
print(f"{len(raw_data)} reports in raw data")


data = raw_data.copy()  # keep raw data
data = data.drop(data[data.id == "999999"].index)
data.faelleCovidAktuell = data.faelleCovidAktuell.fillna(value=0)
data.faelleCovidAktuell = data.faelleCovidAktuell.astype("int")
# newer data contains meldebereiche as list, unhashable -> cast to str for now
if "meldebereiche" in data.columns: 
    data.meldebereiche = data.meldebereiche.astype("str")


data_unique = pd.DataFrame()
for clinic in clinics:
    try:
        data_unique = data_unique.append(
            data[data.id == clinic].drop_duplicates(), ignore_index=True
        )
    except TypeError:
        print(data[data.id == clinic])
data_unique = data_unique.sort_values("meldezeitpunkt")
print(f"{len(data_unique)} unique reports")


report_times = data_unique.meldezeitpunkt.unique()


counts = []
for report_time in report_times:
    up_until = data_unique[data_unique.meldezeitpunkt <= report_time]
    only_newest_status = up_until.drop_duplicates(subset=["id"], keep="last")
    counts_now = {}
    for column in [
        "bettenStatus.statusLowCare",
        "bettenStatus.statusHighCare",
        "bettenStatus.statusECMO",
    ]:
        counts_now[column] = (
            only_newest_status[column].fillna(value="NaN").value_counts(dropna=False)
        )
    counts.append(counts_now)


fig, ax = plt.subplots(3, 1, figsize=(10, 10))


def subplot(ax, column):
    this_counts = {}
    statuses = ["VERFUEGBAR", "BEGRENZT", "NICHT_VERFUEGBAR", "NaN"]
    for status in statuses:
        this_counts[status] = []
        for c in counts:
            try:
                this_counts[status].append(c[column][status])
            except KeyError:
                this_counts[status].append(0)
    ax.stackplot(
        report_times,
        this_counts[statuses[0]],
        this_counts[statuses[1]],
        this_counts[statuses[2]],
        this_counts[statuses[3]],
        labels=statuses,
        colors=["#3CA902", "#F6D50E", "#F60E0E", "#ccc"],
    )
    ax.set_title(column)
    ax.set_ylabel("Clinics")
    ax.set_xlim(datetime(2020, 3, 21), datetime.now())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y.%m.%d"))
    for st in scrape_times:
        ax.axvline(st, alpha=0.2, c="k", lw=0.5)
    ax.grid()
    ax.set_axisbelow(True)


subplot(ax[0], "bettenStatus.statusLowCare")
subplot(ax[1], "bettenStatus.statusHighCare")
subplot(ax[2], "bettenStatus.statusECMO")
fig.tight_layout()
fig.savefig("plot.png", dpi=300)
