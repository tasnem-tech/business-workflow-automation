"""Invoice workflow: validation, idempotent import, approval, payment, and reporting."""
import csv
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS invoices (
 invoice_id TEXT PRIMARY KEY, supplier TEXT NOT NULL, project TEXT NOT NULL,
 amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
 currency TEXT NOT NULL CHECK(currency = 'GBP'),
 due_date TEXT NOT NULL, status TEXT NOT NULL
 CHECK(status IN ('Pending', 'Approved', 'Paid')),
 imported_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT NOT NULL,
 event_type TEXT NOT NULL, details TEXT NOT NULL, occurred_at TEXT NOT NULL
);
"""
REQUIRED = ('invoice_id', 'supplier', 'project', 'amount', 'currency', 'due_date')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def validate(row):
    missing = [k for k in REQUIRED if not str(row.get(k, '') or '').strip()]
    if missing:
        raise ValueError('Missing required fields: ' + ', '.join(missing))
    invoice_id = row['invoice_id'].strip()
    try:
        amount = Decimal(row['amount'].strip())
        if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
            raise ValueError('Amount must be nonnegative with at most 2 decimal places')
        cents = int(amount * 100)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('Invalid amount: ' + str(exc)) from exc
    if row['currency'].strip().upper() != 'GBP':
        raise ValueError('Only GBP is supported')
    try:
        datetime.strptime(row['due_date'].strip(), '%Y-%m-%d')
    except ValueError as exc:
        raise ValueError('Invalid due_date; expected YYYY-MM-DD') from exc
    return (invoice_id, row['supplier'].strip(), row['project'].strip(), cents,
            'GBP', row['due_date'].strip())


def import_csv(conn, csv_path):
    results = {'inserted': 0, 'duplicates': 0, 'errors': []}
    with open(csv_path, newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or any(k not in reader.fieldnames for k in REQUIRED):
            raise ValueError('CSV headers must include: ' + ', '.join(REQUIRED))
        for line_number, row in enumerate(reader, start=2):
            try:
                values = validate(row)
                stamp = now()
                with conn:
                    cur = conn.execute('''INSERT OR IGNORE INTO invoices
                    (invoice_id,supplier,project,amount_cents,currency,due_date,status,imported_at,updated_at)
                    VALUES (?,?,?,?,?,?,'Pending',?,?)''', (*values, stamp, stamp))
                    if cur.rowcount:
                        conn.execute('INSERT INTO events(invoice_id,event_type,details,occurred_at) VALUES (?,?,?,?)',
                                     (values[0], 'IMPORTED', 'Created from CSV', stamp))
                        results['inserted'] += 1
                    else:
                        results['duplicates'] += 1
            except ValueError as exc:
                results['errors'].append({'line': line_number, 'reason': str(exc)})
    return results


def transition(conn, invoice_id, new_status):
    allowed = {'Pending': 'Approved', 'Approved': 'Paid'}
    with conn:
        invoice = conn.execute('SELECT status FROM invoices WHERE invoice_id=?', (invoice_id,)).fetchone()
        if not invoice:
            raise ValueError('Invoice not found')
        old = invoice['status']
        if allowed.get(old) != new_status:
            raise ValueError(f'Invalid transition: {old} -> {new_status}')
        stamp = now()
        conn.execute('UPDATE invoices SET status=?, updated_at=? WHERE invoice_id=?',
                     (new_status, stamp, invoice_id))
        conn.execute('INSERT INTO events(invoice_id,event_type,details,occurred_at) VALUES (?,?,?,?)',
                     (invoice_id, 'STATUS_CHANGED', f'{old} -> {new_status}', stamp))


def invoices(conn, status=None):
    if status:
        rows = conn.execute('SELECT * FROM invoices WHERE status=? ORDER BY due_date,invoice_id', (status,))
    else:
        rows = conn.execute('SELECT * FROM invoices ORDER BY due_date,invoice_id')
    return [dict(row) for row in rows]


def supplier_summary(conn):
    rows = conn.execute('''SELECT supplier, status, COUNT(*) AS invoice_count,
       SUM(amount_cents) AS total_cents FROM invoices
       GROUP BY supplier,status ORDER BY supplier,status''')
    return [dict(row) for row in rows]


def events(conn):
    return [dict(r) for r in conn.execute('SELECT * FROM events ORDER BY id DESC LIMIT 100')]
