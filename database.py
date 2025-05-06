import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_token TEXT UNIQUE,
            chat_id INTEGER,
            withdrawal_method TEXT,
            withdrawal_address TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Invoices (
            id TEXT PRIMARY KEY,
            merchant_id INTEGER,
            amount REAL,
            description TEXT,
            status TEXT,
            payment_method TEXT,
            created_at TEXT,
            FOREIGN KEY (merchant_id) REFERENCES Merchants(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT,
            amount_paid REAL,
            commission REAL,
            net_amount REAL,
            paid_at TEXT,
            FOREIGN KEY (invoice_id) REFERENCES Invoices(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER,
            amount REAL,
            method TEXT,
            address TEXT,
            status TEXT,
            requested_at TEXT,
            FOREIGN KEY (merchant_id) REFERENCES Merchants(id)
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()