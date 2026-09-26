# GSleep2Intervals

A Python script to sync Garmin Connect sleep and wellness data to Intervals.icu API.

## Features

- Upload single day, multiple days, or missing days of sleep/wellness data
- Secure credential storage in YAML file (CLI) or environment variables (Vercel)
- Logging to track uploads and avoid duplicates
- Automatic detection of missing data
- Deployable to Vercel as a Serverless Function with scheduled cron jobs

## Setup

### Option A: Local CLI Usage

1. Clone this repository
2. Copy `credentials.yaml.template` to `credentials.yaml`
3. Edit `credentials.yaml` with your Garmin Connect and Intervals.icu credentials
4. Install dependencies: `pip install -r requirements.txt`

### Option B: Vercel Deployment

1. Clone this repository
2. Push to GitHub
3. Import the project in Vercel
4. Set the required environment variables in Vercel:
   - `GARMIN_EMAIL`
   - `GARMIN_PASSWORD`
   - `INTERVALS_API_KEY`
   - `INTERVALS_ATHLETE_ID`
5. Deploy

## Usage

### CLI Mode

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

### Vercel API Mode

The Vercel deployment provides a REST API endpoint at `/api/sync` that accepts POST requests.

**Request:**
```bash
curl -X POST https://your-app.vercel.app/api/sync \
  -H "Content-Type: application/json" \
  -d '{"days": 7, "dry_run": false}'
```

**Request Body Parameters:**
- `days` (number, optional): Number of recent days to sync (default: 7)
- `dry_run` (boolean, optional): Test without uploading (default: false)
- `start_date` (string, optional): Custom start date in YYYY-MM-DD format
- `end_date` (string, optional): Custom end date in YYYY-MM-DD format
- `missing` (boolean, optional): Only upload missing days
- `date` (string, optional): Single date to sync in YYYY-MM-DD format

**Environment Variables:**
- `GARMIN_EMAIL` (required): Your Garmin Connect email
- `GARMIN_PASSWORD` (required): Your Garmin Connect password
- `INTERVALS_API_KEY` (required): Your Intervals.icu API key
- `INTERVALS_ATHLETE_ID` (required): Your Intervals.icu athlete ID
- `SYNC_DAYS` (optional): Default number of days to sync (default: 7)
- `DRY_RUN` (optional): Set to "true" to always run in dry-run mode

### Scheduled Sync (Cron Job)

The project includes a Vercel Cron Job configuration that automatically syncs data daily at 3:00 AM UTC. This is configured in `vercel.json`. You can modify the schedule in your Vercel project settings.

## Credentials

### For CLI Mode

The `credentials.yaml` file should contain:

```yaml
garmin:
  email: "your_garmin_email@example.com"
  password: "your_garmin_password"

intervals_icu:
  api_key: "your_intervals_icu_api_key"
  athlete_id: your_intervals_icu_athlete_id
```

### For Vercel Mode

Set these environment variables in your Vercel project:
- `GARMIN_EMAIL`
- `GARMIN_PASSWORD`
- `INTERVALS_API_KEY`
- `INTERVALS_ATHLETE_ID`

## Logging

- **CLI Mode:** All uploads and errors are logged to `gsleep2intervals.log`
- **Vercel Mode:** Logs are available in the Vercel function logs

## Project Structure

```
.
├── main.py              # Main CLI script
├── api/
│   └── sync.py          # Vercel Serverless Function
├── vercel.json          # Vercel configuration
├── requirements.txt     # Python dependencies
└── README.md
```

## Notes

- The `main.py` script has been cleaned to remove all mock data generation functions
- The Vercel deployment uses the same core logic as the CLI version
- For security, never commit your credentials file or expose environment variables
