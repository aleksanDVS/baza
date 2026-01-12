import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Magazynier Pro Cloud", layout="wide", page_icon="🧾")

# Connect to Supabase using Secrets
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd połączenia! Sprawdź Secrets w Streamlit Cloud.")
    st.stop()

# --- 2. LOGGING FUNCTION ---
def zapisz_dziennik(akcja, szczegoly):
    try:
        # Schema columns: data, akcja, szczegoly, uzytkownik
        supabase.table("dziennik").insert({
            "data": datetime.now().isoformat(),
            "akcja": akcja, 
            "szczegoly": szczegoly,
            "uzytkownik": "Admin"
        }).execute()
    except:
        pass 

# --- 3. NAVIGATION ---
menu = st.sidebar.radio("Nawigacja", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "📜 Historia"])

# --- 4. MODULES ---

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki i Bilans")
    try:
        # Fetching tables
        res_p = supabase.table("produkty").select("*").execute()
        res_s = supabase.table("sprzedaz").select("*").execute()
        df_p = pd.DataFrame(res_p.data)
        df_s = pd.DataFrame(res_s.data)

        if not df_p.empty:
            c1, c2 = st.columns(2)
            c1.metric("Liczba Produktów", len(df_p))
            total_income = df_s['suma'].sum() if not df_s.empty else 0
            c2.metric("Całkowity Przychód", f"{total_income:,.2f} zł")
            
            st.divider()
            st.subheader("Aktualne stany")
            st.dataframe(df_p[['nazwa', 'liczba', 'cena']], use_container_width=True)
        else:
            st.info("Baza danych jest pusta.")
    except Exception as e:
        st.error(f"Błąd Dashboardu: {e}")

# --- WAREHOUSE (MAGAZYN) ---
elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    try:
        res_kat = supabase.table("kategoria").select("*").execute()
        df_kat = pd.DataFrame(res_kat.data)

        if df_kat.empty:
            st.warning("Dodaj najpierw kategorię!")
        else:
            with st.expander("➕ Dodaj produkt"):
                with st.form("add_p", clear_on_submit=True):
                    nazwa = st.text_input("Nazwa produktu")
                    kat_id = st.selectbox("Kategoria", df_kat['id'].tolist(), 
                                          format_func=lambda x: df_kat[df_kat['id']==x]['nazwa'].values[0])
                    c1, c2 = st.columns(2)
                    ilosc = c1.number_input("Ilość", min_value=1)
                    cena = c2.number_input("Cena", min_value=0.0)
                    
                    if st.form_submit_button("Zapisz"):
                        supabase.table("produkty").insert({
                            "nazwa": nazwa, "liczba": ilosc, "cena": cena, "kategoria_id": kat_id
                        }).execute()
                        zapisz_dziennik("DODANIE", f"Dodano: {nazwa}")
                        st.success("Dodano!")
                        st.rerun()

        res_p = supabase.table("produkty").select("*").execute()
        if res_p.data:
            df_p = pd.DataFrame(res_p.data)
            st.dataframe(df_p, use_container_width=True)
            
            st.subheader("🗑️ Usuń produkt")
            with st.form("del"):
                to_del = st.selectbox("Wybierz do usunięcia", df_p['id'].tolist(), 
                                      format_func=lambda x: df_p[df_p['id']==x]['nazwa'].values[0])
                if st.form_submit_button("Usuń trwale"):
                    supabase.table("produkty").delete().eq("id", to_del).execute()
                    zapisz_dziennik("USUNIĘCIE", f"Usunięto ID: {to_del}")
                    st.rerun()
    except Exception as e:
        st.error(f"Błąd Magazynu: {e}")

# --- SALES (SPRZEDAŻ) ---
elif menu == "💸 Sprzedaż":
    st.title("Nowa Sprzedaż")
    try:
        res_p = supabase.table("produkty").select("*").gt("liczba", 0).execute()
        df_p = pd.DataFrame(res_p.data)
        if not df_p.empty:
            with st.form("sale"):
                p_id = st.selectbox("Produkt", df_p['id'].tolist(), 
                                    format_func=lambda x: df_p[df_p['id
