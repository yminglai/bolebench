#!/usr/bin/env python3
"""Human-baseline scorer for BoleBench exam submissions.

Input: one or more CSVs (the quiz's Download-results format, or the Google Sheet's
File->Download->CSV of the 'responses' tab). Columns:
  [timestamp,] who, email, tier, score, version, item_id, choice, conf, sec, flipped, both_below_baseline

Rules implemented (documented in datasheet):
  - A/B orientation: `choice` is already CANONICAL (the quiz records the un-flipped
    choice; `flipped` is bookkeeping only). No correction needed here.
  - EFFORT FILTER: a submission is tagged speed_run if median sec/item < 15
    or total time < 300s. Kept in raw output, excluded from baseline stats.
  - Known-groups: stats reported per tier (student / 1-2 papers / 3+ / senior).
  - Kill flag: both_below_baseline graded against truth (both sigma <= 0.1).

Usage: score_humans.py submissions/*.csv --answers data/answers.jsonl
"""
import argparse, csv, json, statistics, sys
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("csvs", nargs="+")
ap.add_argument("--answers", default="../bolebench/data/answers.jsonl")
args = ap.parse_args()

answers = {}
for line in open(args.answers):
    a = json.loads(line)
    if a["item_id"].startswith("pick"):
        answers[a["item_id"]] = a

subs = defaultdict(list)  # (who, email, version) -> rows
for path in args.csvs:
    with open(path) as f:
        for row in csv.DictReader(f):
            key = (row.get("who") or "anon", row.get("email") or "", row.get("version") or "")
            subs[key].append(row)

print(f"{'who':<14}{'tier':<28}{'n':>3} {'acc':>6} {'med_sec':>8} {'flags':>6}  status")
tiers = defaultdict(list)
for (who, email, ver), rows in sorted(subs.items()):
    secs = [float(r["sec"] or 0) for r in rows]
    med = statistics.median(secs) if secs else 0
    total = sum(secs)
    speed_run = med < 15 or total < 300
    hits = flags_ok = flags_n = n = 0
    for r in rows:
        a = answers.get(r["item_id"])
        if not a:
            continue
        n += 1
        hits += r["choice"] == a["winner"]
        if str(r.get("both_below_baseline", "false")).lower() == "true":
            flags_n += 1
            flags_ok += a["sigma_A"] <= 0.1 and a["sigma_B"] <= 0.1
    tier = rows[0].get("tier") or "?"
    status = "SPEED-RUN (excluded)" if speed_run else "ok"
    if not speed_run and n:
        tiers[tier].append(hits / n)
    fl = f"{flags_ok}/{flags_n}" if flags_n else "-"
    print(f"{who:<14}{tier[:26]:<28}{n:>3} {hits/max(n,1):>6.2f} {med:>8.0f} {fl:>6}  status={status}  email={email}")

print("\n== known-groups (speed-runs excluded) ==")
for t, accs in sorted(tiers.items()):
    print(f"  {t:<30} n={len(accs)}  mean acc={sum(accs)/len(accs):.3f}")
