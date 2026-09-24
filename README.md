# GSleep2Intervals

A Python script to sync Garmin Connect sleep and wellness data to Intervals.icu API.

## Features

- Upload single day, multiple days, or missing days of sleep/wellness data
- Secure credential storage in YAML file
- Logging to track uploads and avoid duplicates
- Automatic detection of missing data

## Setup

1. Clone this repository
2. Copy `credentials.yaml.template` to `credentials.yaml`
3. Edit `credentials.yaml` with your Garmin Connect and Intervals.icu credentials
4. Install dependencies: `pip install -r requirements.txt`

## Usage

```bash
# Upload single day
python main.py --date 2024-01-01

# Upload multiple days
python main.py --start-date 2024-01-01 --end-date 2024-01-10

# Upload missing days (last 30 days)
python main.py --missing --days 30

# Upload all data from last 7 days
python main.py --recent 7

# Dry run (check without uploading)
python main.py --dry-run --start-date 2024-01-01 --end-date 2024-01-10
```

## Credentials

The `credentials.yaml` file should contain:

```yaml
garmin:
  email: "your_garmin_email@example.com"
  password: "your_garmin_password"

intervals_icu:
  api_key: "your_intervals_icu_api_key"
  athlete_id: your_intervals_icu_athlete_id
```

## Logging

All uploads and errors are logged to `gsleep2intervals.log` to track progress and avoid duplicate uploads.
