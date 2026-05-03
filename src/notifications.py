import subprocess
import os
from datetime import datetime

def send_macos_notification(title: str, message: str, sound: str = "default"):
    if os.getenv('ENABLE_NOTIFICATIONS', 'true').lower() != 'true':
        return False
    
    try:
        script = f'''
        display notification "{message}" with title "{title}" sound name "{sound}"
        '''
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False

def notify_poll_failure(error_msg: str):
    send_macos_notification(
        title="WattWise Poll Failed",
        message=f"Poll failed: {error_msg[:50]}...",
        sound="Basso"
    )

def notify_bill_due(bill_period: str, due_date: str, amount: float):
    send_macos_notification(
        title="Bill Payment Due",
        message=f"Bill {bill_period}: ₦{amount:.2f} due {due_date}",
        sound="Glass"
    )

def notify_data_stale(days: int):
    send_macos_notification(
        title="WattWise Data Stale",
        message=f"Data is {days} days old - API may be down",
        sound="Ping"
    )

if __name__ == '__main__':
    send_macos_notification("Test Notification", "WattWise Dashboard notification system is working!")
    print("Test notification sent - check macOS notifications")
