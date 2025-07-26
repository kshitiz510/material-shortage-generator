# streamlit_app.py
import streamlit as st
import pandas as pd
import re
from io import BytesIO

# ---------------- Core Logic ----------------
def normalize_codes(df, col):
    return (
        df[col]
          .astype(str)
          .str.strip()
          .str.replace(r"\.0+$","", regex=True)
    )

@st.cache_data
def load_data(plan_file, bom_file, stock_file, sap_col='SAP'):
    plan = pd.read_excel(plan_file)
    bom = pd.read_excel(bom_file)
    stock = pd.read_excel(stock_file, header=1)

    # Normalize key columns
    plan[sap_col] = normalize_codes(plan, sap_col)
    bom['Material'] = normalize_codes(bom, 'Material')
    bom['Component Material'] = normalize_codes(bom, 'Component Material')
    stock['Material'] = normalize_codes(stock, 'Material')

    # Drop missing SAP
    plan = plan[plan[sap_col] != 'nan']

    # Identify date columns by exclusion
    ignore = {sap_col,'Brand','Size','OS','Version','Aug 2025 Plan',
              'PCB','SPEAKER','PWER CORD','WALL MOUNT','KEY IR','THERMACOL'}
    date_cols = [c for c in plan.columns if c not in ignore]
    if not date_cols:
        raise ValueError(f"No date columns found. Headers: {plan.columns.tolist()}")

    # Wide -> long
    plan_long = (
        plan[[sap_col] + date_cols]
        .melt(id_vars=[sap_col], value_vars=date_cols,
              var_name='Date', value_name='PlannedQty')
        .dropna(subset=['PlannedQty'])
        .assign(PlannedQty=lambda df: df['PlannedQty'].astype(int))
    )

    # Rename BOM description columns by position
    cols = list(bom.columns)
    mat_idx = cols.index('Material')
    comp_idx = cols.index('Component Material')
    tv_desc_col = cols[mat_idx+1]
    comp_desc_col = cols[comp_idx+1]
    bom = bom.rename(columns={tv_desc_col:'TV Description', comp_desc_col:'Component Description'})

    # Merge plan with BOM
    enriched = (
        plan_long
        .merge(
            bom[['Material','TV Description',
                 'Component Material','Component Description','Comp. Qty (CUn)']],
            left_on=sap_col, right_on='Material', how='left'
        )
        .assign(RequiredQty=lambda df: df['PlannedQty'] * df['Comp. Qty (CUn)'])
    )

    # Aggregate demand per TV and component
    grouped = (
        enriched.groupby([
            'Date', sap_col, 'TV Description',
            'Component Material','Component Description'
        ], as_index=False)['RequiredQty'].sum()
    )

    # Prepare initial stock lookup
    stock_lookup = (
        stock[['Material','Today Stock']]
        .rename(columns={'Material':'Component Material','Today Stock':'InitialStock'})
        .assign(InitialStock=lambda df: df['InitialStock'].fillna(0).astype(float))
    )

    # Merge to bring in initial stock
    df = grouped.merge(stock_lookup, on='Component Material', how='left')
    df['InitialStock'] = df['InitialStock'].fillna(0)

    # Allocate stock per component across rows in date+SAP order
    records = []
    for comp, sub in df.groupby('Component Material'):
        rem = sub['InitialStock'].iloc[0]
        # iterate sorted demands
        for _, row in sub.sort_values(['Date', sap_col]).iterrows():
            req = row['RequiredQty']
            available_before = rem
            if rem >= req:
                short = 0
                rem -= req
            else:
                short = req - rem
                rem = 0
            records.append({
                'Date': row['Date'],
                sap_col: row[sap_col],
                'TV Description': row['TV Description'],
                'Component Material': comp,
                'Component Description': row['Component Description'],
                'RequiredQty': req,
                'AvailableBefore': available_before,
                'Shortage': short
            })
    result = pd.DataFrame(records)

    # Filter only where shortage > 0
    shortage = result[result['Shortage'] > 0].reset_index(drop=True)
    return shortage

# -------------- Streamlit UI --------------
st.set_page_config(page_title='Material Shortage Dashboard', layout='wide')
st.title('📊 Real-Time Shortage Dashboard')

st.sidebar.header('Upload Files')
plan_file = st.sidebar.file_uploader('Production Plan (Excel)', type=['xlsx'])
bom_file = st.sidebar.file_uploader('SAP BOM (Excel)', type=['xlsx'])
stock_file = st.sidebar.file_uploader('Stock Report (Excel)', type=['xlsx'])

if plan_file and bom_file and stock_file:
    df_short = load_data(plan_file, bom_file, stock_file)
    st.subheader('Shortage Report')
    st.dataframe(df_short)

    buffer = BytesIO()
    df_short.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button('📥 Download Shortage Report', data=buffer,
                       file_name='shortage_report.xlsx',
                       mime='application/vnd.ms-excel')
else:
    st.info('Upload all three files to generate the live shortage report.')
