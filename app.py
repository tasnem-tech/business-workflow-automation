"""Streamlit user interface for the local invoice workflow demo."""
import io
import os
from pathlib import Path
import pandas as pd
import streamlit as st
from src.workflow import connect, import_csv, transition, invoices, supplier_summary, events

st.set_page_config(page_title='FlowLedger | Invoice Operations', page_icon='📊', layout='wide')
st.title('FlowLedger')
st.caption('Business workflow automation | Local invoice processing demo')
DB = Path(os.environ.get('FLOWLEDGER_DB', 'runtime/flowledger.db'))
conn = connect(DB)

with st.sidebar:
    st.header('Import invoices')
    upload = st.file_uploader('Upload invoice CSV', type=['csv'])
    if upload and st.button('Validate & import', type='primary'):
        try:
            data = upload.getvalue()
            if len(data) > 2_000_000:
                st.error('CSV must be 2 MB or smaller')
            else:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
                    tmp.write(data)
                    tmp_path = tmp.name
                try:
                    result = import_csv(conn, tmp_path)
                finally:
                    os.unlink(tmp_path)
                st.success(f"Inserted {result['inserted']} | Duplicates {result['duplicates']}")
                if result['errors']:
                    st.warning(f"Rejected rows: {len(result['errors'])}")
                    st.dataframe(pd.DataFrame(result['errors']), hide_index=True)
        except (ValueError, UnicodeError) as exc:
            st.error(str(exc))
    st.caption('Start with data/sample_invoices.csv. No external accounts required.')

rows = invoices(conn)
count = len(rows)
pending = sum(r['amount_cents'] for r in rows if r['status'] == 'Pending')
approved = sum(r['amount_cents'] for r in rows if r['status'] == 'Approved')
paid = sum(r['amount_cents'] for r in rows if r['status'] == 'Paid')
a,b,c,d = st.columns(4)
a.metric('Invoices', count)
b.metric('Pending', f'£{pending/100:,.2f}')
c.metric('Approved', f'£{approved/100:,.2f}')
d.metric('Paid', f'£{paid/100:,.2f}')

tab1, tab2, tab3 = st.tabs(['Invoice queue', 'Supplier reporting', 'Audit log'])
with tab1:
    status_filter = st.selectbox('Status', ['All', 'Pending', 'Approved', 'Paid'])
    visible = rows if status_filter == 'All' else [r for r in rows if r['status'] == status_filter]
    table = [{**r, 'amount_gbp': r['amount_cents']/100} for r in visible]
    if table:
        st.dataframe(pd.DataFrame(table)[['invoice_id','supplier','project','amount_gbp','due_date','status']],
                     use_container_width=True, hide_index=True)
    else:
        st.info('No invoices to display. Import the sample CSV to get started.')
    if rows:
        st.subheader('Advance invoice status')
        invoice_id = st.selectbox('Invoice', [r['invoice_id'] for r in rows])
        current = next(r['status'] for r in rows if r['invoice_id'] == invoice_id)
        next_status = {'Pending': 'Approved', 'Approved': 'Paid'}.get(current)
        st.write(f'Current: **{current}**')
        if next_status and st.button(f'Mark as {next_status}'):
            try:
                transition(conn, invoice_id, next_status)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        elif not next_status:
            st.caption('Paid invoices are final in this demo.')
with tab2:
    summary = supplier_summary(conn)
    if summary:
        frame = pd.DataFrame(summary)
        frame['total_gbp'] = frame['total_cents']/100
        st.dataframe(frame[['supplier','status','invoice_count','total_gbp']], hide_index=True, use_container_width=True)
        csv_data = frame[['supplier','status','invoice_count','total_gbp']].to_csv(index=False)
        st.download_button('Download supplier summary CSV', csv_data, 'supplier_summary.csv', 'text/csv')
    else:
        st.info('Import invoices to generate a supplier report.')
with tab3:
    log = events(conn)
    if log:
        st.dataframe(pd.DataFrame(log), hide_index=True, use_container_width=True)
    else:
        st.info('Events will appear after invoice imports and status changes.')
st.divider()
st.caption('Demo only: no authentication, external payments, or live financial integrations. Use synthetic data.')
