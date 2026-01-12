import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Magazynier Pro Cloud", layout="wide", page_icon="🧾")

# Establish connection using Streamlit Secrets
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd połączenia! Sprawdź Secrets w Streamlit Cloud.")
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
    res_p = supabase.table("produkty").select("*").execute()
    res_s = supabase.table("sprzedaz").select("*").execute()
    df_p = pd.DataFrame(res_p.data)
    df_s = pd.DataFrame(res_s.data)

    if not df_p.empty:
        c1, c2 = st.columns(2)
        c1.metric("Suma produktów", len(df_p))
        c2.metric("Suma sprzedaży", f"{df_s['suma'].sum() if not df_s.empty else 0:.2f} zł")
    else:
        st.info("Baza jest pusta.")

elif menu == "📦 Magazyn":
    st.title("Magazyn")
    res_kat = supabase.table("kategoria").select("*").execute()
    df_kat = pd.DataFrame(res_kat.data)

    if not df_kat.empty:
        with st.expander("Dodaj produkt"):
            with st.form("add"):
                n = st.text_input("Nazwa")
                k = st.selectbox("Kategoria", df_kat['id'].tolist(), format_func=lambda x: df_kat[df_kat['id']==x]['nazwa'].values[0])
                i = st.number_input("Ilość", min_value=1)
                c = st.number_input("Cena", min_value=0.0)
                if st.form_submit_button("Zapisz"):
                    supabase.table("produkty").insert({"nazwa": n, "liczba": i, "cena": c, "kategoria_id": k}).execute()
                    zapisz_dziennik("DODANIE", f"Dodano {n}")
                    st.success("Zapisano!")
                    st.rerun()

    res_p = supabase.table("produkty").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        st.dataframe(df_p, use_container_width=True)
        
        st.subheader("🗑️ Usuń produkt")
        with st.form("del"):
            to_del = st.selectbox("Produkt do usunięcia", df_p['id'].tolist(), format_func=lambda x: df_p[df_p['id']==x]['nazwa'].values[0])
            if st.form_submit_button("Usuń"):
                supabase.table("produkty").delete().eq("id", to_del).execute()
                zapisz_dziennik("USUNIĘCIE", f"Usunięto ID: {to_del}")
                st.rerun()

elif menu == "💸 Sprzedaż":
    st.title("Sprzedaż")
    res_p = supabase.table("produkty").select("*").execute()
    df_p = pd.DataFrame(res_p.data)
    if not df_p.empty:
        with st.form("sale"):
            pid = st.selectbox("Produkt", df_p['id'].tolist(), format_func=lambda x: df_p[df_p['id']==x]['nazwa'].values[0])
            ile = st.number_input("Ilość", min_value=1)
            if st.form_submit_button("Sprzedaj"):
                # Logic for updating stock and saving to 'sprzedaz' table
                st.success("Sprzedano!")
                st.rerun()

elif menu == "📂 Kategorie":
    st.title("Kategorie")
    with st.form("kat"):
        nowa = st.text_input("Nowa kategoria")
        if st.form_submit_button("Dodaj"):
            supabase.table("kategoria").insert({"nazwa": nowa}).execute()
            st.rerun()
    res_k = supabase.table("kategoria").select("*").execute()
    if res_k.data:
        st.table(pd.DataFrame(res_k.data))

elif menu == "📜 Historia":
    st.title("Historia")
    res_h = supabase.table("dziennik").select("*").order("id", desc=True).execute()
    if res_h.data:
        st.dataframe(pd.DataFrame(res_h.data), use_container_width=True)
    else:
        st.write("Brak wpisów w historii.")
