import sys
import os
from pathlib import Path
uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
f = os.path.realpath(__file__)
sys.path.append(uppath(f, 2))

import pandas as pd
from collections import defaultdict
from datetime import datetime
import common.ol_const as olc
import common.ol_util as olu

"""
    6dc-row-count-report
    1. Scans data/quotes directory structure (YYYY/MM/DD/)
    2. Finds all files matching pattern "sq-TRADES-AAPL2*"
    3. Counts rows in each file (excluding header)
    4. Generates monthly summary CSV: data/quotes/summary/row-count-YYYY-MM.csv
"""


def count_rows_in_file(file_path):
    """
    Count rows in a CSV file (excluding header).

    Args:
        file_path: Path to the CSV file

    Returns:
        Number of data rows (excluding header), or 0 if error
    """
    try:
        # Using wc -l would be faster, but pandas ensures we handle CSV correctly
        df = pd.read_csv(file_path)
        return len(df)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0


def generate_row_count_reports(quotes_dir="data/quotes", pattern_prefix="sq-TRADES-AAPL2"):
    """
    Generate monthly row count reports for option quote files.

    Args:
        quotes_dir: Base directory containing quote files
        pattern_prefix: File name pattern to match
    """
    quotes_path = Path(quotes_dir)
    summary_dir = quotes_path / "summary"
    summary_dir.mkdir(exist_ok=True)

    # Dictionary to collect data by year-month
    monthly_data = defaultdict(list)

    print(olu.tn() + f"Scanning {quotes_dir} for files matching '{pattern_prefix}*'...")

    # Walk through YYYY/MM/DD structure
    for year_dir in sorted(quotes_path.iterdir()):
        if not year_dir.is_dir() or year_dir.name == "summary":
            continue

        year = year_dir.name
        if not year.isdigit():
            continue

        print(olu.tn() + f"Processing year: {year}")

        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue

            month = month_dir.name
            if not month.isdigit():
                continue

            year_month_key = f"{year}-{month}"
            print(olu.tn() + f"  Processing month: {year_month_key}")

            files_processed = 0

            for day_dir in sorted(month_dir.iterdir()):
                if not day_dir.is_dir():
                    continue

                day = day_dir.name
                if not day.isdigit():
                    continue

                # Find all matching files in this day directory
                for file_path in day_dir.glob(f"{pattern_prefix}*.csv"):
                    row_count = count_rows_in_file(file_path)

                    monthly_data[year_month_key].append({
                        'date': f"{year}-{month}-{day}",
                        'file_name': file_path.name,
                        'row_count': row_count,
                        'file_path': str(file_path.relative_to(quotes_path))
                    })
                    files_processed += 1

            if files_processed > 0:
                print(olu.tn() + f"    Found {files_processed} files")

    # Generate monthly CSV reports
    print(olu.tn() + f"Generating monthly summary reports...")

    for year_month, records in sorted(monthly_data.items()):
        df = pd.DataFrame(records)

        # Sort by date and file name
        df = df.sort_values(['date', 'file_name'])

        # Calculate summary statistics
        total_rows = df['row_count'].sum()
        total_files = len(df)
        avg_rows = df['row_count'].mean() if total_files > 0 else 0

        # Save to CSV
        output_file = summary_dir / f"row-count-{year_month}.csv"
        df.to_csv(output_file, index=False)

        print(olu.tn() + f"  {year_month}: {total_files} files, {total_rows:,} total rows, {avg_rows:.1f} avg rows/file -> {output_file}")

    print(olu.tn() + f"Generated {len(monthly_data)} monthly reports in {summary_dir}")
    return len(monthly_data)


if __name__ == "__main__":
    start_time = datetime.now()
    print(olu.tn() + "6dc-row-count-report Starting!")

    # Allow command line override of quotes directory
    quotes_dir = sys.argv[1] if len(sys.argv) > 1 else "data/quotes"

    report_count = generate_row_count_reports(quotes_dir)

    duration = (datetime.now() - start_time).total_seconds()
    print(olu.tn() + f"6dc-row-count-report done! Generated {report_count} reports in {duration:.1f} seconds")
