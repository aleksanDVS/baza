import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Magazynier Pro Cloud", layout="wide", page_icon="🧾")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd połączenia! Sprawdź Secrets.")
    st.stop()

# --- 2. HELPER FUNCTIONS ---
def zapisz_dziennik(akcja, szczegoly):
    try:
        supabase.table("dziennik").insert({
            "data": datetime.now().isoformat(),
            "akcja": akcja, 
            "szczegoly": szczegoly,
            "uzytkownik": "System"
        }).execute()
    except:
        pass 

# --- 3. NAVIGATION ---
menu = st.sidebar.radio("Nawigacja", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "📜 Historia"])

# --- 4. MODULES ---

if menu == "📊 Dashboard":
    st.title("Statystyki")
    try:
        res_p = supabase.table("produkty").select("*").execute()
        df_p = pd.DataFrame(res_p.data)
        if not df_p.empty:
            st.metric("Produkty w bazie", len(df_p))
            st.dataframe(df_p, use_container_width=True)
    except:
        st.info("Baza danych produktów jest pusta lub niedostępna.")

elif menu == "📦 Magazyn":
    st.title("Magazyn")
    res_kat = supabase.table("kategoria").select("*").execute()
    df_kat = pd.DataFrame(res_kat.data)

    if not df_kat.empty:
        with st.expander("➕ Dodaj produkt"):
            with st.form("add"):
                n = st.text_input("Nazwa")
                k = st.selectbox("Kategoria", df_kat['id'].tolist(), format_func=lambda x: df_kat[df_kat['id']==x]['nazwa'].values[0])
                i = st.number_input("Ilość", min_value=1)
                c = st.number_input("Cena", min_value=0.0)
                if st.form_submit_button("Zapisz"):
                    supabase.table("produkty").insert({"nazwa": n, "liczba": i, "cena": c, "kategoria_id": k}).execute()
                    zapisz_dziennik("DODANIE", f"Dodano {n}")
                    st.rerun()

    res_p = supabase.table("produkty").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        st.dataframe(df_p, use_container_width=True)
        
        st.subheader("🗑️ Usuń produkt")
        with st.form("del"):
            to_del = st.selectbox("Wybierz do usunięcia", df_p['id'].tolist(), format_func=lambda x: df_p[df_p['id']==x]['nazwa'].values[0])
            if st.form_submit_button("Usuń"):
                supabase.table("produkty").delete().eq("id", to_del).execute()
                zapisz_dziennik("USUNIĘCIE", f"Usunięto ID: {to_del}")
                st.rerun()

elif menu == "💸 Sprzedaż":
    st.title("Sprzedaż")
    res_p = supabase.table("produkty").select("*").gt("liczba", 0).execute()
    df_p = pd.DataFrame(res_p.data)
    if not df_p.empty:
        with st.form("sale"):
            pid = st.selectbox("Produkt", df_p['id'].tolist(), format_func=lambda x: df_p[df_p['id']==x]['nazwa'].values[0])
            ile = st.number_input("Ilość", min_value=1)
            if st.form_submit_button("Sprzedaj"):
                row = df_p[df_p['id'] == pid].iloc[0]
                if ile <= row['liczba']:
                    nowa = int(row['liczba'] - ile)
                    suma = ile * float(row['cena'])
                    supabase.table("produkty").update({"liczba": nowa}).eq("id", pid).execute()
                    supabase.table("sprzedaz").insert({"produkt_id": pid, "ilosc": ile, "suma": suma}).execute()
                    zapisz_dziennik("SPRZEDAŻ", f"Sprzedano {ile}x {row['nazwa']}")
                    st.success("Sukces!")
                    st.rerun()

elif menu == "📂 Kategorie":
    st.title("Kategorie")
    with st.form("kat"):
        nowa = st.text_input("Nazwa kategorii")
        if st.form_submit_button("Dodaj"):
            supabase.table("kategoria").insert({"nazwa": nowa}).execute()
            st.rerun()
    res = supabase.table("kategoria").select("*").execute()
    if res.data:
        st.table(pd.DataFrame(res.data)[['nazwa']])

# --- FIXED HISTORY SECTION ---
elif menu == "📜 Historia":
    st.title("Historia")
    try:
        # We wrap this in a try block so a DB error doesn't kill the app
        res_h = supabase.table("dziennik").select("*").order("id", desc=True).execute()
        if res_h.data:
            df_h = pd.DataFrame(res_h.data)
            st.dataframe(df_h, use_container_width=True)
        else:
            st.info("Historia jest pusta.")
    except Exception as e:
        st.error("Błąd dostępu do tabeli 'dziennik'.")
        st.warning("Upewnij się, że w Supabase SQL Editorze uruchomiłeś: ALTER TABLE dziennik DISABLE ROW LEVEL SECURITY;")
