import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# --- CONFIG ---
st.set_page_config(page_title="Magazynier Pro", layout="wide")
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- DASHBOARD ---
st.title("📊 Dashboard")
try:
    # After running the SQL fix, use lowercase names
    res_p = supabase.table("produkty").select("*").execute()
    df_p = pd.DataFrame(res_p.data)
    
    if not df_p.empty:
        st.metric("Liczba produktów", len(df_p))
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("Baza jest pusta.")
except Exception as e:
    st.error(f"Błąd: {e}")

# --- LOGGING FUNCTION ---
def zapisz_dziennik(akcja, szczegoly):
    # Matches columns: data, akcja, szczegoly, uzytkownik
    supabase.table("dziennik").insert({
        "data": datetime.now().isoformat(),
        "akcja": akcja, 
        "szczegoly": szczegoly,
        "uzytkownik": "Admin"
    }).execute()
