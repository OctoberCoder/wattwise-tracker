import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv('DATABASE_URL', None)
if not DATABASE_URL:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'wattwise.db')
    DATABASE_URL = f'sqlite:///{DB_PATH}'

def get_engine():
    if DATABASE_URL.startswith('sqlite'):
        os.makedirs(os.path.dirname(DATABASE_URL.replace('sqlite:///', '')), exist_ok=True)
        engine = create_engine(DATABASE_URL)
        # For SQLite, create tables if they don't exist
        try:
            with engine.connect() as conn:
                conn.execute(text('SELECT 1 FROM consumption LIMIT 1'))
        except:
            init_db()
        return engine
    
    # For Azure SQL Database, convert ODBC connection string to SQLAlchemy format
    if 'Driver=' in DATABASE_URL and 'Server=' in DATABASE_URL:
        # Parse ODBC string and convert to sqlalchemy format
        import re
        driver = re.search(r'Driver=\{(.+?)\}', DATABASE_URL)
        server = re.search(r'Server=tcp:(.+?),', DATABASE_URL)
        database = re.search(r'Database=(.+?);', DATABASE_URL)
        uid = re.search(r'Uid=(.+?);', DATABASE_URL)
        pwd = re.search(r'Pwd=(.+?);', DATABASE_URL)
        
        if all([driver, server, database, uid, pwd]):
            sqlalchemy_url = f"mssql+pyodbc://{uid.group(1)}:{pwd.group(1)}@{server.group(1)}/{database.group(1)}?driver={driver.group(1).replace(' ', '+')}"
            return create_engine(sqlalchemy_url)
    
    return create_engine(DATABASE_URL)

def init_db():
    engine = get_engine()
    with engine.connect() as conn:
        # Create consumption table
        conn.execute(text('''
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'consumption') AND type in (N'U'))
            BEGIN
            CREATE TABLE consumption (
                id INT IDENTITY(1,1) PRIMARY KEY,
                snapshot_date NVARCHAR(50) NOT NULL,
                cumulative_kwh FLOAT NOT NULL,
                residual_amount FLOAT,
                source NVARCHAR(50) DEFAULT 'api',
                created_at NVARCHAR(50) DEFAULT CONVERT(NVARCHAR, GETDATE(), 120)
            )
            END
        '''))
        
        # Create rates table
        conn.execute(text('''
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'rates') AND type in (N'U'))
            BEGIN
            CREATE TABLE rates (
                id INT IDENTITY(1,1) PRIMARY KEY,
                rate_per_kwh FLOAT NOT NULL,
                effective_from NVARCHAR(50) NOT NULL,
                effective_to NVARCHAR(50),
                source NVARCHAR(50) DEFAULT 'manual',
                created_at NVARCHAR(50) DEFAULT CONVERT(NVARCHAR, GETDATE(), 120)
            )
            END
        '''))
        
        # Create billing table
        conn.execute(text('''
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'billing') AND type in (N'U'))
            BEGIN
            CREATE TABLE billing (
                id INT IDENTITY(1,1) PRIMARY KEY,
                billing_period_start NVARCHAR(50) NOT NULL,
                billing_period_end NVARCHAR(50) NOT NULL,
                total_kwh FLOAT,
                total_bill_amount FLOAT NOT NULL,
                payment_gateway FLOAT DEFAULT 0,
                payment_transfer FLOAT DEFAULT 0,
                service_charge FLOAT,
                due_date NVARCHAR(50),
                payment_status NVARCHAR(50) DEFAULT 'unpaid',
                source NVARCHAR(50) DEFAULT 'api',
                created_at NVARCHAR(50) DEFAULT CONVERT(NVARCHAR, GETDATE(), 120)
            )
            END
        '''))
        
        # Create payments table
        conn.execute(text('''
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'payments') AND type in (N'U'))
            BEGIN
            CREATE TABLE payments (
                id INT IDENTITY(1,1) PRIMARY KEY,
                payment_date NVARCHAR(50) NOT NULL,
                amount FLOAT NOT NULL,
                method NVARCHAR(50) NOT NULL,
                reference NVARCHAR(255),
                source NVARCHAR(50) DEFAULT 'manual',
                created_at NVARCHAR(50) DEFAULT CONVERT(NVARCHAR, GETDATE(), 120)
            )
            END
        '''))
        
        conn.commit()

def execute_query(query: str, params: dict = None) -> List[Dict[str, Any]]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        if result.returns_rows:
            return [dict(row) for row in result]
        conn.commit()
        return []

def execute_insert(query: str, params: dict = None) -> int:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        conn.commit()
        return result.lastrowid

def insert_consumption(snapshot_date: str, cumulative_kwh: float, 
                       residual_amount: Optional[float] = None, source: str = 'api') -> int:
    return execute_insert('''
        INSERT INTO consumption (snapshot_date, cumulative_kwh, residual_amount, source)
        VALUES (:snapshot_date, :cumulative_kwh, :residual_amount, :source)
    ''', {'snapshot_date': snapshot_date, 'cumulative_kwh': cumulative_kwh, 
          'residual_amount': residual_amount, 'source': source})

def get_latest_consumption() -> Optional[Dict[str, Any]]:
    results = execute_query('SELECT * FROM consumption ORDER BY snapshot_date DESC LIMIT 1')
    return results[0] if results else None

def insert_rate(rate_per_kwh: float, effective_from: str, 
                effective_to: Optional[str] = None, source: str = 'manual') -> int:
    return execute_insert('''
        INSERT INTO rates (rate_per_kwh, effective_from, effective_to, source)
        VALUES (:rate_per_kwh, :effective_from, :effective_to, :source)
    ''', {'rate_per_kwh': rate_per_kwh, 'effective_from': effective_from, 
          'effective_to': effective_to, 'source': source})

def get_active_rate(date: str) -> Optional[Dict[str, Any]]:
    results = execute_query('''
        SELECT * FROM rates 
        WHERE effective_from <= :date 
        AND (effective_to IS NULL OR effective_to >= :date)
        ORDER BY effective_from DESC LIMIT 1
    ''', {'date': date})
    return results[0] if results else None

def get_all_rates() -> List[Dict[str, Any]]:
    return execute_query('SELECT * FROM rates ORDER BY effective_from DESC')

def insert_billing(period_start: str, period_end: str, total_kwh: Optional[float],
                  total_amount: float, gateway: float = 0, transfer: float = 0,
                  service_charge: Optional[float] = None, due_date: Optional[str] = None,
                  status: str = 'unpaid', source: str = 'api') -> int:
    return execute_insert('''
        INSERT INTO billing (
            billing_period_start, billing_period_end, total_kwh, total_bill_amount,
            payment_gateway, payment_transfer, service_charge, due_date, payment_status, source
        ) VALUES (:start, :end, :kwh, :amount, :gateway, :transfer, :charge, :due, :status, :source)
    ''', {'start': period_start, 'end': period_end, 'kwh': total_kwh, 'amount': total_amount,
          'gateway': gateway, 'transfer': transfer, 'charge': service_charge, 'due': due_date,
          'status': status, 'source': source})

def get_all_billing() -> List[Dict[str, Any]]:
    return execute_query('SELECT * FROM billing ORDER BY billing_period_start DESC')

def insert_payment(payment_date: str, amount: float, method: str,
                    reference: Optional[str] = None, source: str = 'manual') -> int:
    return execute_insert('''
        INSERT INTO payments (payment_date, amount, method, reference, source)
        VALUES (:date, :amount, :method, :reference, :source)
    ''', {'date': payment_date, 'amount': amount, 'method': method, 
          'reference': reference, 'source': source})

def get_payments_by_period(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    return execute_query('''
        SELECT * FROM payments 
        WHERE payment_date BETWEEN :start AND :end
        ORDER BY payment_date DESC
    ''', {'start': start_date, 'end': end_date})

if __name__ == '__main__':
    init_db()
    print(f'Database initialized with DATABASE_URL: {DATABASE_URL}')
