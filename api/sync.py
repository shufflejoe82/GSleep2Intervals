"""
Vercel Serverless Function for syncing Garmin Connect data to Intervals.icu

This endpoint can be triggered by:
- HTTP POST requests (manual or scheduled)
- Vercel Cron Jobs

Environment Variables required:
- GARMIN_EMAIL: Garmin Connect email
- GARMIN_PASSWORD: Garmin Connect password
- INTERVALS_API_KEY: Intervals.icu API key
- INTERVALS_ATHLETE_ID: Intervals.icu athlete ID

Optional:
- SYNC_DAYS: Number of days to sync (default: 7)
- DRY_RUN: Set to "true" to test without uploading
"""

import os
import json
import logging
from datetime import date, timedelta
from typing import Dict, Any

# Configure logging for Vercel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import from parent module
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import DataUploader, CredentialsError


def get_config_from_env() -> Dict[str, Any]:
    """Build configuration from environment variables."""
    config = {}
    
    # Garmin credentials
    garmin_email = os.environ.get('GARMIN_EMAIL')
    garmin_password = os.environ.get('GARMIN_PASSWORD')
    
    if not garmin_email or not garmin_password:
        raise CredentialsError("GARMIN_EMAIL and GARMIN_PASSWORD environment variables are required")
    
    config['garmin'] = {
        'email': garmin_email,
        'password': garmin_password
    }
    
    # Intervals.icu credentials
    intervals_api_key = os.environ.get('INTERVALS_API_KEY')
    intervals_athlete_id = os.environ.get('INTERVALS_ATHLETE_ID')
    
    if not intervals_api_key or not intervals_athlete_id:
        raise CredentialsError("INTERVALS_API_KEY and INTERVALS_ATHLETE_ID environment variables are required")
    
    try:
        config['intervals_icu'] = {
            'api_key': intervals_api_key,
            'athlete_id': int(intervals_athlete_id)
        }
    except ValueError:
        raise CredentialsError("INTERVALS_ATHLETE_ID must be a valid integer")
    
    return config


def build_response(status_code: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a proper Vercel response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        },
        'body': json.dumps(data)
    }


def handler(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vercel Serverless Function handler.
    
    Supports:
    - POST /api/sync - Sync data with optional body parameters
    
    Request body (JSON):
    {
        "days": 7,           // Number of days to sync (default: 7)
        "dry_run": false,    // Test without uploading
        "start_date": "2024-01-01",  // Custom start date
        "end_date": "2024-01-10"     // Custom end date
    }
    """
    try:
        # Get configuration from environment
        config = get_config_from_env()
        
        # Parse request
        body = {}
        if request.get('body'):
            try:
                body = json.loads(request['body'])
            except (json.JSONDecodeError, TypeError):
                body = {}
        
        # Get parameters from body or query string
        days = int(body.get('days', 7))
        dry_run = body.get('dry_run', False) or os.environ.get('DRY_RUN', '').lower() == 'true'
        start_date = body.get('start_date')
        end_date = body.get('end_date')
        missing = body.get('missing', False)
        recent = body.get('recent')
        single_date = body.get('date')
        
        # Initialize uploader
        logger.info("Initializing data uploader...")
        uploader = DataUploader(config)
        uploader.initialize_clients()
        
        stats = None
        
        if single_date:
            # Single day upload
            logger.info(f"Syncing single date: {single_date}")
            success = uploader.upload_single_day(single_date, dry_run)
            stats = {
                'status': 'success' if success else 'failed',
                'date': single_date,
                'dry_run': dry_run
            }
        
        elif start_date and end_date:
            # Date range upload
            logger.info(f"Syncing date range: {start_date} to {end_date}")
            stats = uploader.upload_date_range(start_date, end_date, dry_run)
            stats['dry_run'] = dry_run
        
        elif missing:
            # Calculate date range for missing days
            end_date_calc = date.today().strftime('%Y-%m-%d')
            start_date_calc = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            logger.info(f"Checking for missing data between {start_date_calc} and {end_date_calc}")
            stats = uploader.upload_missing_days(start_date_calc, end_date_calc, dry_run)
            stats['dry_run'] = dry_run
        
        else:
            # Default: recent days
            end_date_calc = date.today().strftime('%Y-%m-%d')
            start_date_calc = (date.today() - timedelta(days=days - 1)).strftime('%Y-%m-%d')
            
            logger.info(f"Syncing last {days} days: {start_date_calc} to {end_date_calc}")
            stats = uploader.upload_date_range(start_date_calc, end_date_calc, dry_run)
            stats['dry_run'] = dry_run
        
        # Close clients
        uploader.close()
        
        # Add metadata
        result = {
            'success': True,
            'stats': stats,
            'timestamp': date.today().isoformat()
        }
        
        logger.info(f"Sync completed: {json.dumps(stats)}")
        return build_response(200, result)
    
    except CredentialsError as e:
        logger.error(f"Credentials error: {e}")
        return build_response(400, {
            'success': False,
            'error': str(e),
            'hint': 'Please set all required environment variables: GARMIN_EMAIL, GARMIN_PASSWORD, INTERVALS_API_KEY, INTERVALS_ATHLETE_ID'
        })
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return build_response(500, {
            'success': False,
            'error': str(e),
            'type': type(e).__name__
        })


# For local testing
def local_test():
    """Test the function locally."""
    import os
    
    # Set environment variables for testing
    os.environ['GARMIN_EMAIL'] = 'test@example.com'
    os.environ['GARMIN_PASSWORD'] = 'test_password'
    os.environ['INTERVALS_API_KEY'] = 'test_api_key'
    os.environ['INTERVALS_ATHLETE_ID'] = '12345'
    os.environ['DRY_RUN'] = 'true'
    
    # Create a mock request
    request = {
        'body': json.dumps({'days': 7, 'dry_run': True})
    }
    
    result = handler(request)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    local_test()
