# FlowLedger | Business Workflow Automation

**A local-first invoice operations dashboard that turns supplier CSV files into a traceable approval workflow and downloadable reporting.**

![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-red) ![SQLite](https://img.shields.io/badge/SQLite-local%20database-lightgrey) ![Tests](https://img.shields.io/badge/Tests-unittest-green)

## Why this project exists

Small operations teams often manage supplier invoices through email and spreadsheets. This leads to duplicate entries, unclear approval status, and manual month-end reporting. FlowLedger demonstrates a small, testable automation pipeline: **CSV import → validation → deduplication → status approval → audit trail → supplier summary**.

## Features

- Upload invoice CSV files and validate required fields, amounts, currency, and dates
- Deduplicate by invoice ID on repeated imports
- Track `Pending → Approved → Paid` transitions
- Review a timestamped audit log of imports and status changes
- Filter invoices and monitor pending, approved, and paid totals
- Export supplier-level summaries as CSV
- Store data locally in SQLite, with no paid API or cloud account required
- Run automated unit tests in GitHub Actions

## Screenshot

Run the app locally and add your own screenshot to `docs/dashboard.png`. The project does **not** claim a hosted live demo.

## Tech stack

Python 3.11+, Streamlit, pandas, SQLite (Python standard library), unittest, GitHub Actions.

## Run locally on macOS

Open **Terminal** and navigate to the extracted project folder:

```bash
cd ~/Downloads/business-workflow-automation
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit will print a local URL, normally `http://localhost:8501`. Upload `data/sample_invoices.csv` from the sidebar.

To stop, press `Control + C`. For subsequent runs:

```bash
cd ~/Downloads/business-workflow-automation
source .venv/bin/activate
python -m streamlit run app.py
```

If `python3 --version` fails, install Python 3.11 or newer first. The app stores its database in `runtime/flowledger.db`, which is excluded from Git.

## CSV input format

Required columns:

| invoice_id | supplier | project | amount | currency | due_date |
|---|---|---|---:|---|---|
| INV-1001 | Northstar Supplies | Office Renovation | 1250.00 | GBP | 2026-12-05 |

- `invoice_id` must be unique; reimporting an existing ID skips it, without overwriting its status.
- Amounts must be nonnegative and have no more than two decimal places.
- Only GBP is supported in this demo.
- Due dates must be in `YYYY-MM-DD` format.
- Rejected rows are displayed after import. The app continues with other valid rows.

Try `data/sample_invalid.csv` to demonstrate validation errors.

## Test

```bash
python -m unittest discover -s tests -v
```

Tests cover repeated imports, state transitions, invalid amounts, supplier totals, and partial CSV rejection.

## Architecture

```text
Supplier CSV
    |
    v
CSV parser + validation
    |
    v
SQLite invoices table (unique invoice_id)
    |                      |
    v                      v
Status transitions       Audit events
    |                      |
    +----------+-----------+
               |
               v
     Streamlit dashboard
               |
               v
       Supplier CSV export
```

## Repository structure

```text
app.py                     Streamlit interface
src/workflow.py            Validation, import, transitions, queries
src/__init__.py            Python package marker
data/sample_invoices.csv    Synthetic example invoices
data/sample_invalid.csv     Synthetic validation examples
tests/test_workflow.py      Automated tests
.github/workflows/tests.yml CI test workflow
requirements.txt           App dependencies
```

## Security and limitations

**Portfolio demonstration, not production accounting software.** The app has no login, role-based permissions, real payment processing, email integration, or external API. It is intended for a single trusted local user with synthetic sample data. Do not expose the Streamlit server publicly or upload sensitive real invoices. Duplicate invoice IDs are skipped even if subsequent rows contain changed amounts. A production version would need authentication, authorization, database migrations, backups, supplier matching, stronger audit controls, and explicit correction/reversal workflows.

## Roadmap

- [ ] Role-based approvals and authentication
- [ ] Supplier-specific monthly reports
- [ ] Scheduled imports from a secured mailbox
- [ ] PostgreSQL and deployment
- [ ] Duplicate detection using supplier + reference + amount

## Portfolio summary

Built a Python and Streamlit business workflow prototype that automates invoice CSV validation, idempotent import, approval tracking, audit logging, and supplier reporting using SQLite. Added unit tests and GitHub Actions CI to demonstrate maintainable automation practices.

## License

MIT. All sample suppliers and invoices are fictional.
