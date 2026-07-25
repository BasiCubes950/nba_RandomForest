#!/usr/bin/env python3
"""Combine all CSV files in the Seasons/ directory into a single CSV.

Usage:
    python3 combine_seasons.py
    python3 combine_seasons.py -i Seasons -o all_seasons.csv
"""
import os
import glob
import argparse
import sys

def find_csv_files(input_dir):
    pattern = os.path.join(input_dir, "*.csv")
    return sorted(glob.glob(pattern))


def season_start_year(season_str):
    """Convert season string like '1996-97' or '96-97' or '1996' to starting year int.

    Returns None if it cannot be parsed.
    """
    if season_str is None:
        return None
    s = str(season_str).strip()
    # plain year
    if s.isdigit():
        if len(s) == 4:
            return int(s)
        if len(s) == 2:
            v = int(s)
            return 2000 + v if v <= 30 else 1900 + v

    # patterns like '1996-97' or '96-97' or '1996-1997'
    if "-" in s:
        left = s.split("-")[0]
        left = left.strip()
        if left.isdigit():
            if len(left) == 4:
                return int(left)
            if len(left) == 2:
                v = int(left)
                return 2000 + v if v <= 30 else 1900 + v

    return None


def filter_df_by_max_year(df, max_year):
    """Filter rows in df where season starting year <= max_year.

    Uses the `season` column if present; otherwise attempts to keep the whole df.
    """
    if max_year is None:
        return df

    if "season" in df.columns:
        # parse each season value to start year
        start_years = df["season"].apply(season_start_year)
        mask = start_years.notnull() & (start_years <= max_year)
        # keep rows without a parseable season conservatively
        mask = mask | start_years.isnull()
        return df[mask]

    # no season column — cannot reliably filter rows, keep df unchanged
    return df

def combine_csvs(files):
    try:
        import pandas as pd
    except Exception:
        print("pandas is required. Install with: python3 -m pip install pandas")
        sys.exit(1)

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"Warning: could not read {f}: {e}")
            continue
        # record source so we can trace rows back to files
        df["_source_file"] = os.path.basename(f)
        frames.append(df)

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True, sort=False)
    return combined

def main():
    parser = argparse.ArgumentParser(description="Combine Seasons CSV files into one CSV")
    parser.add_argument("-i", "--input-dir", default="Seasons", help="Directory containing season CSV files")
    parser.add_argument("-o", "--output", default="train.csv", help="Output CSV path")
    parser.add_argument("-m", "--max-season", default="21-22",
                        help="Maximum season to include. Accepts formats like 1996, 1996-97, 96-97.")
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"Input directory not found: {args.input_dir}")
        sys.exit(1)

    files = find_csv_files(args.input_dir)
    if not files:
        print(f"No CSV files found in {args.input_dir}")
        sys.exit(1)
    # interpret max season
    max_year = None
    if args.max_season:
        max_year = season_start_year(args.max_season)
        if max_year is None:
            print(f"Could not parse --max-season value: {args.max_season}")
            sys.exit(1)

    print(f"Found {len(files)} files. Combining up to season start year: {max_year if max_year else 'ALL'}...")

    # combine while filtering per-file to avoid loading extra rows
    try:
        import pandas as pd
    except Exception:
        print("pandas is required. Install with: python3 -m pip install pandas")
        sys.exit(1)

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"Warning: could not read {f}: {e}")
            continue
        df["_source_file"] = os.path.basename(f)
        # if the dataframe doesn't have a `season` column, infer it from the filename
        if "season" not in df.columns:
            base = os.path.splitext(os.path.basename(f))[0]
            df["season"] = base

        # apply season filter
        df = filter_df_by_max_year(df, max_year)
        if df.empty:
            continue
        frames.append(df)

    if not frames:
        print("No data combined after filtering. Exiting.")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True, sort=False)
    if combined is None:
        print("No data combined. Exiting.")
        sys.exit(1)

    # Normalize Rk: set all non-zero or missing values to 1, keep existing 0s as 0
    if "Rk" in combined.columns:
        combined["Rk"] = pd.to_numeric(combined["Rk"], errors="coerce")
        # keep zeros, set NaN/non-zero to 1
        combined.loc[combined["Rk"] != 0, "Rk"] = 1
        combined["Rk"] = combined["Rk"].fillna(1).astype(int)

    combined.to_csv(args.output, index=False)
    print(f"Wrote {len(combined)} rows to {args.output}")


if __name__ == "__main__":
    main()
