
import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
# ใส่ลิงก์ CSV จาก Google Sheets ของคุณที่นี่
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQhFyFtoL4NEmNYZHceOSpeuVS-vymIBrIhGr5L50bd1QM-Bgh95ewCQWCMPwZJnKdLIt7m0ZywiFZ-/pub?gid=276106846&single=true&output=csv"

st.set_page_config(page_title="Steam Capacity Calculator", layout="wide")

@st.cache_data(ttl=60)
def load_and_clean_data(url):
    try:
        df_raw = pd.read_csv(url, header=None)
        
        # 1. ค้นหาแถวที่มีขนาดท่อ (มองหาแถวที่มีเลข 15)
        pipe_row_idx = None
        for idx, row in df_raw.iterrows():
            if str(row[2]).strip() == '15':
                pipe_row_idx = idx
                break
        
        if pipe_row_idx is None:
            st.error("ไม่พบแถวที่ระบุขนาดท่อในไฟล์")
            return None

        # ดึง Pipe Sizes
        pipe_sizes = [str(int(float(x))) for x in df_raw.iloc[pipe_row_idx, 2:].dropna()]
        
        # 2. เริ่มดึงข้อมูล
        data_start_idx = pipe_row_idx + 4 
        data = df_raw.iloc[data_start_idx:].copy()
        
        headers = ['Pressure_bar_g', 'Velocity_m_s'] + pipe_sizes
        data = data.iloc[:, :len(headers)]
        data.columns = headers
        
        # 3. ล้างข้อมูลช่องว่าง/คอมม่า
        def clean_val(x):
            if pd.isna(x) or str(x).strip() == '': return np.nan
            return str(x).replace(' ', '').replace(',', '').strip()

        for col in data.columns:
            data[col] = data[col].apply(clean_val)
        
        data['Pressure_bar_g'] = data['Pressure_bar_g'].ffill()
        data = data.apply(pd.to_numeric, errors='coerce')
        data = data.dropna(subset=['Velocity_m_s'])
        
        return data

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
        return None

# --- UI ---
st.title("Saturated Steam Pipeline Capacity (Schedule 40)")
st.markdown("---")

df = load_and_clean_data(SHEET_URL)

if df is not None:
    # Sidebar สำหรับเลือกค่า
    st.sidebar.header("Input Parameters")
    p_val = st.sidebar.selectbox("Pressure (bar g)", sorted(df['Pressure_bar_g'].unique()))
    v_val = st.sidebar.selectbox("Velocity (m/s)", sorted(df['Velocity_m_s'].unique()))
    
    # กรองข้อมูล
    result_row = df[(df['Pressure_bar_g'] == p_val) & (df['Velocity_m_s'] == v_val)]
    
    if not result_row.empty:
        # เตรียม DataFrame สำหรับตาราง
        pipe_cols = [c for c in df.columns if c not in ['Pressure_bar_g', 'Velocity_m_s']]
        vals = result_row[pipe_cols].values.flatten()
        
        final_df = pd.DataFrame({
            'Pipe Size (DN)': [int(c) for c in pipe_cols],
            'Capacity (kg/h)': vals
        }).sort_values('Pipe Size (DN)')

        # แสดงผล 2 คอลัมน์ (ตารางข้อมูล | รูปภาพ T-S Diagram)
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.subheader(f"Data for {p_val} bar g @ {v_val} m/s")
            # จัดรูปแบบตาราง
            st.dataframe(
                final_df.style.format({
                    "Pipe Size (DN)": "DN {:g}", 
                    "Capacity (kg/h)": "{:,.0f}"
                }), 
                height=500,
                use_container_width=True,
                hide_index=True
            )
            
        with col2:
            st.subheader("Steam T-S Diagram")
            # แสดงรูปภาพจากลิงก์ภายนอก หรือคุณสามารถใส่ไฟล์ภาพในโฟลเดอร์เดียวกับโค้ดได้
            ts_diagram_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Entropy-temperature_diagram_for_water.svg/800px-Entropy-temperature_diagram_for_water.svg.png"
            st.image(ts_diagram_url, caption="Temperature-Entropy Diagram for Water/Steam", use_container_width=True)
            
            # เพิ่มคำแนะนำเล็กน้อย
            st.info("""
            **T-S Diagram Overview:**
            กราฟนี้แสดงความสัมพันธ์ระหว่างอุณหภูมิ (T) และเอนโทรปี (S) 
            ซึ่งช่วยในการวิเคราะห์สถานะของไอน้ำที่ความดันต่างๆ
            """)
            
    else:
        st.warning("ไม่พบข้อมูลที่ตรงกับเงื่อนไข")

else:
    st.info("โปรดตรวจสอบการตั้งค่า SHEET_URL")
