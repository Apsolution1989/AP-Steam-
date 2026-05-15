import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/YOUR_ID/pub?output=csv"

st.set_page_config(page_title="Steam Capacity & Pipe Price", layout="wide")

# --- DATABASE: PRICE LIST (อ้างอิงจากรูปภาพที่อัปโหลด) ---
# ราคาต่อเส้น (Length 6m)
price_data = {
    "Size": [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150],
    "SML C/S #40": [1150, 1550, 2250, 3050, 3550, 4850, 7850, 10250, 14850, 20550, 26850],
    "ERW C/S #40": [650, 850, 1250, 1750, 2050, 2850, 4550, 5850, 8550, 11850, 15550],
    "SML SUS304 #40S": [4850, 6250, 9550, 13550, 15850, 22550, 35850, 45850, 68550, 92550, 125550]
}
df_price = pd.DataFrame(price_data)

@st.cache_data(ttl=60)
def load_and_clean_data(url):
    try:
        df_raw = pd.read_csv(url, header=None)
        pipe_row_idx = None
        for idx, row in df_raw.iterrows():
            if str(row[2]).strip() == '15':
                pipe_row_idx = idx
                break
        if pipe_row_idx is None: return None

        pipe_sizes = [str(int(float(x))) for x in df_raw.iloc[pipe_row_idx, 2:].dropna()]
        data_start_idx = pipe_row_idx + 4 
        data = df_raw.iloc[data_start_idx:].copy()
        headers = ['Pressure_bar_g', 'Velocity_m_s'] + pipe_sizes
        data = data.iloc[:, :len(headers)]
        data.columns = headers

        def clean_val(x):
            if pd.isna(x) or str(x).strip() == '': return np.nan
            return str(x).replace(' ', '').replace(',', '').strip()

        for col in data.columns:
            data[col] = data[col].apply(clean_val)
        
        data['Pressure_bar_g'] = data['Pressure_bar_g'].ffill()
        data = data.apply(pd.to_numeric, errors='coerce')
        return data.dropna(subset=['Velocity_m_s'])
    except:
        return None

# --- UI ---
st.title("Steam Pipe Capacity & Price List")
st.markdown("---")

df_steam = load_and_clean_data(SHEET_URL)

if df_steam is not None:
    # Sidebar
    st.sidebar.header("Calculation Setting")
    p_val = st.sidebar.selectbox("Pressure (bar g)", sorted(df_steam['Pressure_bar_g'].unique()))
    v_val = st.sidebar.selectbox("Velocity (m/s)", sorted(df_steam['Velocity_m_s'].unique()))
    
    # Filter Steam Data
    res_steam = df_steam[(df_steam['Pressure_bar_g'] == p_val) & (df_steam['Velocity_m_s'] == v_val)]
    
    if not res_steam.empty:
        # Prepare Capacity Table
        pipe_cols = [c for c in df_steam.columns if c not in ['Pressure_bar_g', 'Velocity_m_s']]
        cap_vals = res_steam[pipe_cols].values.flatten()
        
        df_final = pd.DataFrame({
            'Size': [int(c) for c in pipe_cols],
            'Capacity (kg/h)': cap_vals
        })

        # Merge with Price List
        df_final = pd.merge(df_final, df_price, on='Size', how='left')

        # --- Display ---
        col1, col2 = st.columns([4, 6])
        
        with col1:
            st.subheader(f"Steam Capacity ({p_val} bar g)")
            st.dataframe(
                df_final[['Size', 'Capacity (kg/h)']].style.format({
                    "Size": "DN {:g}",
                    "Capacity (kg/h)": "{:,.0f}"
                }),
                height=500, use_container_width=True, hide_index=True
            )
            
        with col2:
            st.subheader("Pipe Price List (THB/6m)")
            # ตารางราคาเปรียบเทียบ 3 ประเภท
            st.dataframe(
                df_final[['Size', 'SML C/S #40', 'ERW C/S #40', 'SML SUS304 #40S']].style.format({
                    "Size": "DN {:g}",
                    "SML C/S #40": "{:,.0f}",
                    "ERW C/S #40": "{:,.0f}",
                    "SML SUS304 #40S": "{:,.0f}"
                }),
                height=500, use_container_width=True, hide_index=True
            )
            
        st.caption("หมายเหตุ: ราคาที่แสดงเป็นราคาประมาณการต่อความยาว 6 เมตร อ้างอิงตามฐานข้อมูล Price List")
    else:
        st.warning("ไม่พบข้อมูล")
else:
    st.info("กรุณาตรวจสอบ SHEET_URL")
