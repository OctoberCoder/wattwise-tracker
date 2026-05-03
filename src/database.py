import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import sqlite3

# Use SQLite for simplicity on Azure App Service
# Azure SQL requires ODBC drivers not available on Linux App Service
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'wattwise.db')

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            cumulative_kwh REAL NOT NULL,
            residual_amount REAL,
            source TEXT NOT NULL DEFAULT 'api',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rate_per_kwh REAL NOT NULL,
            effective_from TEXT NOT NULL,
            effective_to TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            billing_period_start TEXT NOT NULL,
            billing_period_end TEXT NOT NULL,
            total_kwh REAL,
            total_bill_amount REAL NOT NULL,
            payment_gateway REAL DEFAULT 0,
            payment_transfer REAL DEFAULT 0,
            service_charge REAL,
            due_date TEXT,
            payment_status TEXT DEFAULT 'unpaid',
            source TEXT NOT NULL DEFAULT 'api',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_date TEXT NOT NULL,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            reference TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def insert_consumption(snapshot_date: str, cumulative_kwh: float, 
                       residual_amount: Optional[float] = None, source: str = 'api') -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO consumption (snapshot_date, cumulative_kwh, residual_amount, source)
        VALUES (?, ?, ?, ?)
    ''', (snapshot_date, cumulative_kwh, residual_amount, source))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_latest_consumption() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM consumption ORDER BY snapshot_date DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def insert_rate(rate_per_kwh: float, effective_from: str, 
                effective_to: Optional[str] = None, source: str = 'manual') -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO rates (rate_per_kwh, effective_from, effective_to, source)
        VALUES (?, ?, ?, ?)
    ''', (rate_per_kwh, effective_from, effective_to, source))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_active_rate(date: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM rates 
        WHERE effective_from <= ? 
        AND (effective_to IS NULL OR effective_to >= ?)
        ORDER BY effective_from DESC LIMIT 1
    ''', (date, date))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_rates() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM rates ORDER BY effective_from DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_billing(period_start: str, period_end: str, total_kwh: Optional[float],
                  total_amount: float, gateway: float = 0, transfer: float = 0,
                  service_charge: Optional[float] = None, due_date: Optional[str] = None,
                  status: str = 'unpaid', source: str = 'api') -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO billing (
            billing_period_start, billing_period_end, total_kwh, total_bill_amount,
            payment_gateway, payment_transfer, service_charge, due_date, payment_status, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (period_start, period_end, total_kwh, total_amount, 
             gateway, transfer, service_charge, due_date, status, source))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_all_billing() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM billing ORDER BY billing_period_start DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_payment(payment_date: str, amount: float, method: str,
                    reference: Optional[str] = None, source: str = 'manual') -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO payments (payment_date, amount, method, reference, source)
        VALUES (?, ?, ?, ?, ?)
    ''', (payment_date, amount, method, reference, source))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_payments_by_period(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM payments 
        WHERE payment_date BETWEEN ? AND ?
        ORDER BY payment_date DESC
    ''', (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == '__main__':
    init_db()
    print(f'Database initialized at: {DB_PATH}')
