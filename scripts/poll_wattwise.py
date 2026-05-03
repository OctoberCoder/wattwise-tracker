#!/usr/bin/env python3
import sys
import os
import time
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from api_client import create_client_from_env, WattWiseClient
from database import init_db, insert_consumption, get_latest_consumption
from notifications import notify_poll_failure, notify_data_stale

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
STALE_DAYS_THRESHOLD = 30

def poll_with_retry(client: WattWiseClient, method, *args, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            return method(*args)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(RETRY_DELAY * (attempt + 1))
    return None

def main():
    try:
        init_db()
        
        client = create_client_from_env()
        
        if not client.login():
            notify_poll_failure("Login failed")
            print("ERROR: Login failed")
            sys.exit(1)
        
        print(f"Poll started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        meter_data = poll_with_retry(client, client.get_meter_overview)
        if not meter_data:
            notify_poll_failure("No meter data returned")
            print("ERROR: No meter data returned")
            sys.exit(1)
        
        cumulative_kwh = float(meter_data.get('cumulative_total_consumption', 0))
        residual = float(meter_data.get('residual_amount', 0)) if meter_data.get('residual_amount') else None
        
        latest = get_latest_consumption()
        should_insert = True
        if latest:
            latest_date = datetime.fromisoformat(latest['snapshot_date'].replace('Z', '+00:00'))
            hours_since = (datetime.now() - latest_date).total_seconds() / 3600
            if hours_since < 1:
                should_insert = False
                print(f"Skipping poll - last snapshot was {hours_since:.1f} hours ago")
        
        if should_insert:
            insert_consumption(
                snapshot_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                cumulative_kwh=cumulative_kwh,
                residual_amount=residual,
                source='api'
            )
            print(f"Inserted snapshot: {cumulative_kwh:.2f} kWh")
        else:
            print("Skipped - too soon since last poll")
        
        if 'updated_at' in meter_data:
            freshness = client.check_data_freshness(meter_data['updated_at'])
            if freshness['is_stale']:
                notify_data_stale(freshness['days_stale'])
                print(f"WARNING: Data is {freshness['days_stale']} days old")
        
        dashboard_data = poll_with_retry(client, client.get_dashboard_overview)
        if dashboard_data:
            print(f"Dashboard data: {dashboard_data.get('all_time_amount')} bills, {dashboard_data.get('all_units')} kWh")
        
        print("Poll completed successfully")
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: {error_msg}")
        notify_poll_failure(error_msg)
        sys.exit(1)

if __name__ == '__main__':
    main()
