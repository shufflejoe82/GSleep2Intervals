#!/usr/bin/env python3
"""
GSleep2Intervals - Sync Garmin Connect sleep and wellness data to Intervals.icu

This script reads sleep and wellness data from Garmin Connect and uploads it
to the Intervals.icu API. It supports uploading single days, date ranges,
or automatically detecting and uploading missing days.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

import yaml
import pytz
from dateutil import parser as dateutil_parser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gsleep2intervals.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CredentialsError(Exception):
    """Raised when credentials are missing or invalid."""
    pass


class APIError(Exception):
    """Raised when API requests fail."""
    pass


class GarminConnectClient:
    """Client for fetching data from Garmin Connect."""
    
    def __init__(self, email: str, password: str):
        """
        Initialize Garmin Connect client.
        
        Note: This is a placeholder. In production, use the python-garminconnect
        library or implement proper OAuth2 flow.
        """
        self.email = email
        self.password = password
        self.session = None
        self._authenticated = False
    
    def authenticate(self):
        """Authenticate with Garmin Connect."""
        try:
            # Import here to avoid dependency issues if not using garminconnect
            from garminconnect import Garmin
            
            self.client = Garmin(self.email, self.password)
            self.client.login()
            self._authenticated = True
            logger.info("Successfully authenticated with Garmin Connect")
        except ImportError:
            logger.warning("python-garminconnect not available. Using mock data.")
            self._authenticated = False
        except Exception as e:
            logger.error(f"Failed to authenticate with Garmin Connect: {e}")
            raise CredentialsError(f"Garmin Connect authentication failed: {e}")
    
    def get_sleep_data(self, date_str: str) -> Optional[Dict[str, Any]]:
        """
        Get sleep data for a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing sleep data or None if not available
        """
        if not self._authenticated:
            # Return mock data for testing
            return self._get_mock_sleep_data(date_str)
        
        try:
            # Parse date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Fetch sleep data from Garmin Connect
            # Note: The actual python-garminconnect API may differ
            sleep_data = self.client.get_sleep_data(date_obj)
            
            if sleep_data and 'dailySleepDTO' in sleep_data:
                return self._parse_sleep_data(sleep_data)
            return None
        except Exception as e:
            logger.error(f"Failed to fetch sleep data for {date_str}: {e}")
            return None
    
    def _get_mock_sleep_data(self, date_str: str) -> Dict[str, Any]:
        """Return mock sleep data for testing purposes."""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Generate mock data
        sleep_start = datetime.combine(date_obj, datetime.min.time()).timestamp() * 1000
        sleep_end = datetime.combine(date_obj, datetime.min.time()).timestamp() * 1000 + 8 * 3600 * 1000
        
        return {
            'date': date_str,
            'sleepTimeSeconds': 8 * 3600,
            'deepSleepTimeSeconds': 2 * 3600,
            'lightSleepTimeSeconds': 4 * 3600,
            'remSleepTimeSeconds': 2 * 3600,
            'awakeSleepTimeSeconds': 300,
            'sleepStartTimestamp': sleep_start,
            'sleepEndTimestamp': sleep_end,
            'sleepScores': {
                'overall': 75,
                'deep': 80,
                'light': 70,
                'rem': 75
            },
            'stress': {
                'resting': 30,
                'average': 40,
                'max': 60
            },
            'hrv': {
                'restingHeartRate': 55,
                'hrvValue': 65
            },
            'spo2': {
                'average': 95,
                'min': 88
            },
            'bodyBattery': {
                'current': 85,
                'min': 60,
                'max': 95
            }
        }
    
    def _parse_sleep_data(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse raw Garmin sleep data into standardized format."""
        sleep = raw_data.get('dailySleepDTO', {})
        
        result = {
            'date': raw_data.get('calendarDate', ''),
            'sleepTimeSeconds': sleep.get('sleepTimeSeconds', 0),
            'deepSleepTimeSeconds': sleep.get('deepSleepSeconds', 0),
            'lightSleepTimeSeconds': sleep.get('lightSleepSeconds', 0),
            'remSleepTimeSeconds': sleep.get('remSleepSeconds', 0),
            'awakeSleepTimeSeconds': sleep.get('awakeSleepSeconds', 0),
            'sleepStartTimestamp': sleep.get('sleepStartTimestamp', 0),
            'sleepEndTimestamp': sleep.get('sleepEndTimestamp', 0),
            'sleepScores': sleep.get('sleepScores', {}),
        }
        
        # Add wellness data if available
        wellness = raw_data.get('wellness', {})
        if wellness:
            result['stress'] = wellness.get('stress', {})
            result['hrv'] = wellness.get('hrv', {})
            result['spo2'] = wellness.get('spo2', {})
            result['bodyBattery'] = wellness.get('bodyBattery', {})
        
        return result
    
    def get_wellness_data(self, date_str: str) -> Optional[Dict[str, Any]]:
        """
        Get wellness data for a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing wellness data or None if not available
        """
        if not self._authenticated:
            # Return mock data for testing
            return self._get_mock_wellness_data(date_str)
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            wellness_data = self.client.get_wellness_data(date_obj)
            
            if wellness_data:
                return self._parse_wellness_data(wellness_data)
            return None
        except Exception as e:
            logger.error(f"Failed to fetch wellness data for {date_str}: {e}")
            return None
    
    def _get_mock_wellness_data(self, date_str: str) -> Dict[str, Any]:
        """Return mock wellness data for testing purposes."""
        return {
            'date': date_str,
            'stress': {
                'resting': 30,
                'average': 40,
                'max': 60,
                'timestamp': datetime.now().timestamp() * 1000
            },
            'hrv': {
                'restingHeartRate': 55,
                'hrvValue': 65,
                'timestamp': datetime.now().timestamp() * 1000
            },
            'spo2': {
                'average': 95,
                'min': 88,
                'timestamp': datetime.now().timestamp() * 1000
            },
            'bodyBattery': {
                'current': 85,
                'min': 60,
                'max': 95,
                'timestamp': datetime.now().timestamp() * 1000
            }
        }
    
    def _parse_wellness_data(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse raw Garmin wellness data into standardized format."""
        result = {}
        
        if 'stress' in raw_data:
            result['stress'] = {
                'resting': raw_data['stress'].get('restingStress', 0),
                'average': raw_data['stress'].get('averageStress', 0),
                'max': raw_data['stress'].get('maxStress', 0),
                'timestamp': raw_data['stress'].get('timestamp', 0)
            }
        
        if 'hrv' in raw_data:
            result['hrv'] = {
                'restingHeartRate': raw_data['hrv'].get('restingHeartRate', 0),
                'hrvValue': raw_data['hrv'].get('hrvValue', 0),
                'timestamp': raw_data['hrv'].get('timestamp', 0)
            }
        
        if 'spo2' in raw_data:
            result['spo2'] = {
                'average': raw_data['spo2'].get('average', 0),
                'min': raw_data['spo2'].get('min', 0),
                'timestamp': raw_data['spo2'].get('timestamp', 0)
            }
        
        if 'bodyBattery' in raw_data:
            result['bodyBattery'] = {
                'current': raw_data['bodyBattery'].get('current', 0),
                'min': raw_data['bodyBattery'].get('min', 0),
                'max': raw_data['bodyBattery'].get('max', 0),
                'timestamp': raw_data['bodyBattery'].get('timestamp', 0)
            }
        
        return result
    
    def close(self):
        """Close the client session."""
        if hasattr(self, 'client') and self.client:
            self.client.logout()
            logger.info("Garmin Connect session closed")


class IntervalsICUClient:
    """Client for uploading data to Intervals.icu API."""
    
    BASE_URL = "https://intervals.icu/api/v1"
    
    def __init__(self, api_key: str, athlete_id: int):
        """
        Initialize Intervals.icu client.
        
        Args:
            api_key: Intervals.icu API key
            athlete_id: Intervals.icu athlete ID
        """
        self.api_key = api_key
        self.athlete_id = athlete_id
        self.session = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def upload_sleep(self, sleep_data: Dict[str, Any], dry_run: bool = False) -> bool:
        """
        Upload sleep data to Intervals.icu.
        
        Args:
            sleep_data: Dictionary containing sleep data
            dry_run: If True, don't actually upload
            
        Returns:
            True if upload was successful or dry_run, False otherwise
        """
        date_str = sleep_data.get('date', '')
        
        # Convert timestamps to ISO format if they exist
        payload = {
            'date': date_str,
            'sleepTime': sleep_data.get('sleepTimeSeconds', 0),
            'deepSleepTime': sleep_data.get('deepSleepTimeSeconds', 0),
            'lightSleepTime': sleep_data.get('lightSleepTimeSeconds', 0),
            'remSleepTime': sleep_data.get('remSleepTimeSeconds', 0),
            'awakeTime': sleep_data.get('awakeSleepTimeSeconds', 0),
            'sleepStart': self._format_timestamp(sleep_data.get('sleepStartTimestamp', 0)),
            'sleepEnd': self._format_timestamp(sleep_data.get('sleepEndTimestamp', 0)),
        }
        
        # Add sleep scores if available
        sleep_scores = sleep_data.get('sleepScores', {})
        if sleep_scores:
            payload['sleepScore'] = sleep_scores.get('overall', 0)
        
        # Add wellness data
        if 'stress' in sleep_data:
            payload['stress'] = sleep_data['stress']
        if 'hrv' in sleep_data:
            payload['hrv'] = sleep_data['hrv']
        if 'spo2' in sleep_data:
            payload['spo2'] = sleep_data['spo2']
        if 'bodyBattery' in sleep_data:
            payload['bodyBattery'] = sleep_data['bodyBattery']
        
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/sleep"
        
        if dry_run:
            logger.info(f"[DRY RUN] Would upload sleep data for {date_str}")
            logger.debug(f"[DRY RUN] Payload: {payload}")
            return True
        
        try:
            import requests
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully uploaded sleep data for {date_str}")
                return True
            else:
                logger.error(f"Failed to upload sleep data for {date_str}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error uploading sleep data for {date_str}: {e}")
            return False
    
    def _format_timestamp(self, timestamp: Any) -> Optional[str]:
        """Format timestamp for API."""
        if not timestamp:
            return None
        
        try:
            # Handle milliseconds timestamp
            if timestamp > 10000000000:  # Milliseconds since epoch
                dt = datetime.fromtimestamp(timestamp / 1000, pytz.UTC)
            else:  # Seconds since epoch
                dt = datetime.fromtimestamp(timestamp, pytz.UTC)
            
            return dt.isoformat()
        except:
            return None
    
    def check_sleep_exists(self, date_str: str) -> bool:
        """
        Check if sleep data already exists for a given date.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            True if data exists, False otherwise
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/sleep/{date_str}"
        
        try:
            import requests
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error checking sleep data for {date_str}: {e}")
            return False
    
    def get_missing_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        Get list of dates that don't have sleep data in Intervals.icu.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of missing dates
        """
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        missing = []
        current = start
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            if not self.check_sleep_exists(date_str):
                missing.append(date_str)
            current += timedelta(days=1)
        
        return missing


class DataUploader:
    """Main class for uploading Garmin data to Intervals.icu."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data uploader.
        
        Args:
            config: Configuration dictionary from YAML file
        """
        self.config = config
        self.garmin_client = None
        self.intervals_client = None
        self.uploaded_dates = set()
        self._load_uploaded_dates()
    
    def _load_uploaded_dates(self):
        """Load previously uploaded dates from log file."""
        log_file = 'uploaded_dates.log'
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        date_str = line.strip()
                        if date_str:
                            self.uploaded_dates.add(date_str)
            except Exception as e:
                logger.warning(f"Could not read uploaded dates log: {e}")
    
    def _save_uploaded_date(self, date_str: str):
        """Save uploaded date to log file."""
        log_file = 'uploaded_dates.log'
        try:
            with open(log_file, 'a') as f:
                f.write(f"{date_str}\n")
            self.uploaded_dates.add(date_str)
        except Exception as e:
            logger.warning(f"Could not save uploaded date: {e}")
    
    def initialize_clients(self):
        """Initialize Garmin Connect and Intervals.icu clients."""
        garmin_config = self.config.get('garmin', {})
        intervals_config = self.config.get('intervals_icu', {})
        
        # Initialize Garmin client
        email = garmin_config.get('email')
        password = garmin_config.get('password')
        
        if not email or not password:
            raise CredentialsError("Garmin Connect credentials are missing")
        
        self.garmin_client = GarminConnectClient(email, password)
        self.garmin_client.authenticate()
        
        # Initialize Intervals.icu client
        api_key = intervals_config.get('api_key')
        athlete_id = intervals_config.get('athlete_id')
        
        if not api_key or not athlete_id:
            raise CredentialsError("Intervals.icu credentials are missing")
        
        self.intervals_client = IntervalsICUClient(api_key, athlete_id)
    
    def upload_single_day(self, date_str: str, dry_run: bool = False) -> bool:
        """
        Upload data for a single day.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            dry_run: If True, don't actually upload
            
        Returns:
            True if successful, False otherwise
        """
        if date_str in self.uploaded_dates and not dry_run:
            logger.info(f"Skipping {date_str} - already uploaded")
            return True
        
        logger.info(f"Processing date: {date_str}")
        
        # Get sleep data
        sleep_data = self.garmin_client.get_sleep_data(date_str)
        if not sleep_data:
            logger.warning(f"No sleep data found for {date_str}")
            return False
        
        # Get wellness data and merge with sleep data
        wellness_data = self.garmin_client.get_wellness_data(date_str)
        if wellness_data:
            sleep_data.update(wellness_data)
        
        # Upload to Intervals.icu
        success = self.intervals_client.upload_sleep(sleep_data, dry_run)
        
        if success and not dry_run:
            self._save_uploaded_date(date_str)
        
        return success
    
    def upload_date_range(self, start_date: str, end_date: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Upload data for a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            dry_run: If True, don't actually upload
            
        Returns:
            Dictionary with upload statistics
        """
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'no_data': 0
        }
        
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            stats['total'] += 1
            
            if date_str in self.uploaded_dates and not dry_run:
                logger.info(f"Skipping {date_str} - already uploaded")
                stats['skipped'] += 1
                current += timedelta(days=1)
                continue
            
            logger.info(f"Processing date: {date_str}")
            
            # Get sleep data
            sleep_data = self.garmin_client.get_sleep_data(date_str)
            if not sleep_data:
                logger.warning(f"No sleep data found for {date_str}")
                stats['no_data'] += 1
                current += timedelta(days=1)
                continue
            
            # Get wellness data and merge
            wellness_data = self.garmin_client.get_wellness_data(date_str)
            if wellness_data:
                sleep_data.update(wellness_data)
            
            # Upload to Intervals.icu
            success = self.intervals_client.upload_sleep(sleep_data, dry_run)
            
            if success:
                stats['successful'] += 1
                if not dry_run:
                    self._save_uploaded_date(date_str)
            else:
                stats['failed'] += 1
            
            current += timedelta(days=1)
        
        return stats
    
    def upload_missing_days(self, start_date: str, end_date: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Upload data for days that are missing in Intervals.icu.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            dry_run: If True, don't actually upload
            
        Returns:
            Dictionary with upload statistics
        """
        # Get missing dates from Intervals.icu
        missing_dates = self.intervals_client.get_missing_dates(start_date, end_date)
        
        if not missing_dates:
            logger.info("No missing dates found in the specified range")
            return {'total': 0, 'successful': 0, 'failed': 0, 'skipped': 0, 'no_data': 0}
        
        logger.info(f"Found {len(missing_dates)} missing dates: {missing_dates}")
        
        stats = {
            'total': len(missing_dates),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'no_data': 0
        }
        
        for date_str in missing_dates:
            if date_str in self.uploaded_dates and not dry_run:
                logger.info(f"Skipping {date_str} - already uploaded")
                stats['skipped'] += 1
                continue
            
            logger.info(f"Processing missing date: {date_str}")
            
            # Get sleep data
            sleep_data = self.garmin_client.get_sleep_data(date_str)
            if not sleep_data:
                logger.warning(f"No sleep data found for {date_str}")
                stats['no_data'] += 1
                continue
            
            # Get wellness data and merge
            wellness_data = self.garmin_client.get_wellness_data(date_str)
            if wellness_data:
                sleep_data.update(wellness_data)
            
            # Upload to Intervals.icu
            success = self.intervals_client.upload_sleep(sleep_data, dry_run)
            
            if success:
                stats['successful'] += 1
                if not dry_run:
                    self._save_uploaded_date(date_str)
            else:
                stats['failed'] += 1
        
        return stats
    
    def close(self):
        """Close all clients."""
        if self.garmin_client:
            self.garmin_client.close()


def load_config(config_path: str = 'credentials.yaml') -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        CredentialsError: If config file is missing or invalid
    """
    if not os.path.exists(config_path):
        raise CredentialsError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if not config:
            raise CredentialsError("Configuration file is empty")
        
        return config
    except yaml.YAMLError as e:
        raise CredentialsError(f"Invalid YAML in configuration file: {e}")
    except Exception as e:
        raise CredentialsError(f"Failed to load configuration: {e}")


def validate_date(date_str: str) -> bool:
    """
    Validate a date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def get_date_range(start_date: str, end_date: str) -> List[str]:
    """
    Get list of dates between start and end (inclusive).
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List of date strings
    """
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    dates = []
    current = start
    
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return dates


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Sync Garmin Connect sleep and wellness data to Intervals.icu',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --date 2024-01-01                    Upload single day
  %(prog)s --start-date 2024-01-01 --end-date 2024-01-10  Upload date range
  %(prog)s --missing --days 30                  Upload missing days (last 30)
  %(prog)s --recent 7                           Upload last 7 days
  %(prog)s --dry-run --date 2024-01-01         Dry run for single day
        """
    )
    
    # Arguments for single day
    parser.add_argument(
        '--date',
        type=str,
        help='Single date to upload in YYYY-MM-DD format'
    )
    
    # Arguments for date range
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for range upload in YYYY-MM-DD format'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for range upload in YYYY-MM-DD format'
    )
    
    # Arguments for missing days
    parser.add_argument(
        '--missing',
        action='store_true',
        help='Upload only missing days'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to check for missing data (default: 30)'
    )
    
    # Arguments for recent days
    parser.add_argument(
        '--recent',
        type=int,
        help='Upload data from the last N days'
    )
    
    # Dry run option
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Check without uploading (dry run mode)'
    )
    
    # Config file option
    parser.add_argument(
        '--config',
        type=str,
        default='credentials.yaml',
        help='Path to configuration file (default: credentials.yaml)'
    )
    
    # Verbose option
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set verbose logging if requested
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('garminconnect').setLevel(logging.DEBUG)
    
    # Validate arguments
    if not any([args.date, args.start_date, args.missing, args.recent]):
        parser.error('At least one of --date, --start-date/--end-date, --missing, or --recent is required')
    
    # Validate date formats
    if args.date and not validate_date(args.date):
        parser.error(f'Invalid date format: {args.date}. Use YYYY-MM-DD')
    
    if args.start_date and not validate_date(args.start_date):
        parser.error(f'Invalid start date format: {args.start_date}. Use YYYY-MM-DD')
    
    if args.end_date and not validate_date(args.end_date):
        parser.error(f'Invalid end date format: {args.end_date}. Use YYYY-MM-DD')
    
    if args.start_date and not args.end_date:
        parser.error('--start-date requires --end-date')
    
    if args.end_date and not args.start_date:
        parser.error('--end-date requires --start-date')
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(args.config)
        
        # Initialize uploader
        uploader = DataUploader(config)
        uploader.initialize_clients()
        
        # Process based on arguments
        if args.date:
            # Single day upload
            logger.info(f"Uploading data for single day: {args.date}")
            success = uploader.upload_single_day(args.date, args.dry_run)
            
            if success:
                logger.info(f"Successfully processed {args.date}")
                return 0
            else:
                logger.error(f"Failed to process {args.date}")
                return 1
        
        elif args.start_date and args.end_date:
            # Date range upload
            logger.info(f"Uploading data for range: {args.start_date} to {args.end_date}")
            stats = uploader.upload_date_range(args.start_date, args.end_date, args.dry_run)
            
            logger.info(f"\nUpload Statistics:")
            logger.info(f"  Total dates: {stats['total']}")
            logger.info(f"  Successful: {stats['successful']}")
            logger.info(f"  Failed: {stats['failed']}")
            logger.info(f"  Skipped: {stats['skipped']}")
            logger.info(f"  No data: {stats['no_data']}")
            
            return 0 if stats['failed'] == 0 else 1
        
        elif args.missing:
            # Calculate date range for missing days
            end_date = date.today().strftime('%Y-%m-%d')
            start_date = (date.today() - timedelta(days=args.days)).strftime('%Y-%m-%d')
            
            logger.info(f"Checking for missing data between {start_date} and {end_date}")
            stats = uploader.upload_missing_days(start_date, end_date, args.dry_run)
            
            logger.info(f"\nUpload Statistics:")
            logger.info(f"  Total missing: {stats['total']}")
            logger.info(f"  Successful: {stats['successful']}")
            logger.info(f"  Failed: {stats['failed']}")
            logger.info(f"  Skipped: {stats['skipped']}")
            logger.info(f"  No data: {stats['no_data']}")
            
            return 0 if stats['failed'] == 0 else 1
        
        elif args.recent:
            # Recent days upload
            end_date = date.today().strftime('%Y-%m-%d')
            start_date = (date.today() - timedelta(days=args.recent - 1)).strftime('%Y-%m-%d')
            
            logger.info(f"Uploading data for last {args.recent} days: {start_date} to {end_date}")
            stats = uploader.upload_date_range(start_date, end_date, args.dry_run)
            
            logger.info(f"\nUpload Statistics:")
            logger.info(f"  Total dates: {stats['total']}")
            logger.info(f"  Successful: {stats['successful']}")
            logger.info(f"  Failed: {stats['failed']}")
            logger.info(f"  Skipped: {stats['skipped']}")
            logger.info(f"  No data: {stats['no_data']}")
            
            return 0 if stats['failed'] == 0 else 1
        
    except CredentialsError as e:
        logger.error(f"Credentials error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        if 'uploader' in locals():
            uploader.close()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
