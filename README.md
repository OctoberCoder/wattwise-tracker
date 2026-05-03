# WattWiseNG Electricity Dashboard

Simple Streamlit dashboard for tracking electricity consumption, bills, and payments from WattWiseNG metering system.

## Features

- **Dashboard**: Cumulative kWh trends, payment history, cost breakdowns
- **Rate Manager**: Manage electricity rates (₦/kWh) with effective date ranges
- **Bill Upload**: CSV import or manual entry for bills when API data is stale
- **Billing Validation**: Compare calculated costs (kWh × rate) vs actual bill amounts
- **Automated Polling**: Daily 1AM poll via macOS launchd with retry logic
- **macOS Notifications**: Alerts for poll failures, stale data, bill due dates

## Tech Stack

- **Backend**: Python + SQLite (file-based database)
- **Frontend**: Streamlit (low-code dashboard)
- **API**: Reverse-engineered WattWiseNG endpoints (from HAR logs)
- **Scheduling**: macOS launchd (native scheduler)
- **Notifications**: macOS `osascript`

## Quick Start

### 1. Setup
```bash
cd "~/Azure Foundation/opencode"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure Credentials
Edit `.env` with your WattWiseNG credentials:
```
WATTWISE_BASE_URL=https://wattwise.ng/api
WATTWISE_USERNAME=your_email@example.com
WATTWISE_PASSWORD=your_password
```

### 3. Initialize Database
```bash
python3 -c "from src.database import init_db; init_db()"
```

### 4. Run Streamlit Dashboard
```bash
streamlit run streamlit_app/app.py
```

### 5. (Optional) Enable Daily Polling
```bash
# Replace __SCRIPT_DIR__ with actual path
SCRIPT_DIR="/Users/igeorge/Azure Foundation/opencode/launchd"
sed -i '' "s|__SCRIPT_DIR__|$SCRIPT_DIR|g" launchd/com.user.wattwise-sync.plist
cp launchd/com.user.wattwise-sync.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.wattwise-sync.plist
```

## Database Schema

| Table | Purpose |
|-------|---------|
| `consumption` | Snapshots of cumulative kWh + residual debt |
| `rates` | Electricity rates with effective date ranges |
| `billing` | Bill records (period, amounts, payments) |
| `payments` | Individual payment transactions |

## API Endpoints (WattWiseNG)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/user-meter-overview` | GET | Cumulative consumption, residual debt |
| `/api/user-dashboard-overview` | GET | Lifetime stats (total amount, units) |
| `/api/my-monthly-data` | POST | Monthly bills (`{"monthly_option":"present"}`) |
| `/api/my-graph-data` | POST | Payment history (`{"graph_option":"item_7_days"}`) |

**Note**: API data is stale (Jan 2025). Use **Bill Upload** for current data.

## File Structure

```
opencode/
├── src/
│   ├── database.py          # SQLite schema + CRUD
│   ├── api_client.py        # WattWiseNG API client
│   └── notifications.py     # macOS notification helper
├── streamlit_app/
│   ├── app.py              # Main entry point
│   └── pages/
│       ├── dashboard.py      # Trends + payments + costs
│       ├── rate_manager.py   # Rate entry form
│       ├── bill_upload.py    # CSV upload + manual entry
│       └── billing_validate.py # API vs actual comparison
├── launchd/
│   └── com.user.wattwise-sync.plist
├── scripts/
│   └── poll_wattwise.py    # Daily poll script
├── data/                   # SQLite DB + uploads (gitignored)
├── requirements.txt
└── README.md
```

## Known Issues

- **Stale API Data**: WattWiseNG API returns data from Jan 2025; use manual CSV upload for current bills
- **No 15-min Intervals**: Dashboard provides daily/monthly aggregates only
- **Rate Limit**: API allows 60 requests per window (respect `X-RateLimit-*` headers)

## License

MIT
