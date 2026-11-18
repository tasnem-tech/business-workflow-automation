import csv
import tempfile
import unittest
from pathlib import Path
from src.workflow import connect, import_csv, transition, invoices, supplier_summary, validate

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self.tmp.name) / 'test.db')
        self.csv_path = Path(self.tmp.name) / 'sample.csv'
        with self.csv_path.open('w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['invoice_id','supplier','project','amount','currency','due_date'])
            writer.writerow(['INV-1','Vendor A','Project A','10.25','GBP','2026-12-01'])
            writer.writerow(['INV-2','Vendor A','Project A','5.00','GBP','2026-12-02'])
    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()
    def test_import_is_idempotent(self):
        self.assertEqual(import_csv(self.conn, self.csv_path)['inserted'], 2)
        second = import_csv(self.conn, self.csv_path)
        self.assertEqual(second['inserted'], 0)
        self.assertEqual(second['duplicates'], 2)
        self.assertEqual(len(invoices(self.conn)), 2)
    def test_status_flow(self):
        import_csv(self.conn, self.csv_path)
        transition(self.conn, 'INV-1', 'Approved')
        transition(self.conn, 'INV-1', 'Paid')
        self.assertEqual(invoices(self.conn)[0]['status'], 'Paid')
        with self.assertRaises(ValueError):
            transition(self.conn, 'INV-1', 'Pending')
    def test_invalid_amount(self):
        with self.assertRaises(ValueError):
            validate(dict(invoice_id='X', supplier='A', project='B', amount='1.234', currency='GBP', due_date='2026-12-01'))
    def test_supplier_totals(self):
        import_csv(self.conn, self.csv_path)
        self.assertEqual(supplier_summary(self.conn)[0]['total_cents'], 1525)
    def test_rejected_row_does_not_block_valid_rows(self):
        with self.csv_path.open('a') as f:
            f.write('INV-3,Vendor B,Project B,bad,GBP,2026-12-03\n')
        result = import_csv(self.conn, self.csv_path)
        self.assertEqual(result['inserted'], 2)
        self.assertEqual(len(result['errors']), 1)

if __name__ == '__main__':
    unittest.main()
