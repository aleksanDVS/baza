import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. KONFIGURACJA SUPABASE (Wpisz swoje dane) ---
SB_URL = https://pfrgvpybklrmjnyttduo.supabase.co
SB_KEY = sb_publishable_TRb3wyGLDjmxQPXQ2AhtYw_uzmHiwnm
HEADERS = {
    "apikey": SB_KEY,
    "Authorization": f"Bearer {SB_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# --- 2. FUNKCJE API ---
def db_get(table, params=""):
    r = requests.get(f"{SB_URL}/{table}?{params}", headers=HEADERS)
    return r.json()

def db_post(table, data):
    requests.post(f"{SB_URL}/{table}", headers=HEADERS, json=data)

def db_patch(table, data, id_val):
    requests.patch(f"{SB_URL}/{table}?id=eq.{id_val}", headers=HEADERS, json=data)

def db_delete(table, id_val):
    requests.delete(f"{SB_URL}/{table}?id=eq.{id_val}", headers=HEADERS)

def log(akcja, szczegoly):
    db_post("dziennik", {"data": datetime.now().isoformat(), "akcja": akcja, "szczegoly": szczegoly, "uzytkownik": "Admin"})

# --- 3. UI ---
st.set_page_config(page_title="Magazyn Supabase", layout="wide")
menu = st.sidebar.radio("Menu", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "📜 Historia"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki")
    p_data = db_get("produkty", "select=*,kategoria(nazwa)")
    if p_data:
        df = pd.DataFrame(p_data)
        df['kat_nazwa'] = df['kategoria'].apply(lambda x: x['nazwa'] if x else "Brak")
        
        c1, c2 = st.columns(2)
        c1.metric("Produkty w bazie", len(df))
        c2.metric("Suma sztuk", int(df['liczba'].sum()))
        st.bar_chart(df.set_index('nazwa')['liczba'])

# --- MAGAZYN ---
elif menu == "📦 Magazyn":
    st.title("Magazyn")
    kat_data = db_get("kategoria")
    df_k = pd.DataFrame(kat_data)

    with st.expander("Dodaj produkt"):
        n = st.text_input("Nazwa")
        k_name = st.selectbox("Kategoria", df_k['nazwa'].tolist() if not df_k.empty else [])
        l = st.number_input("Ilość", min_value=0)
        c = st.number_input("Cena", min_value=0.0)
        if st.button("Zapisz"):
            k_id = df_k[df_k['nazwa'] == k_name]['id'].values[0]
            db_post("produkty", {"nazwa": n, "liczba": l, "cena": c, "kategoria_id": int(k_id)})
            log("DODANIE", f"Produkt: {n}")
            st.rerun()

    prods = db_get("produkty", "select=*,kategoria(nazwa)")
    if prods:
        st.table(pd.DataFrame(prods))

# --- SPRZEDAŻ ---
elif menu == "💸 Sprzedaż":
    st.title("Sprzedaż")
    prods = db_get("produkty", "liczba=gt.0")
    if prods:
        df_p = pd.DataFrame(prods)
        wybrany = st.selectbox("Produkt", df_p['nazwa'].tolist())
        ile = st.number_input("Ile sztuk", min_value=1)
        if st.button("Sprzedaj"):
            row = df_p[df_p['nazwa'] == wybrany].iloc[0]
            if ile <= row['liczba']:
                nowa_ilosc = int(row['liczba'] - ile)
                suma = ile * float(row['cena'])
                db_patch("produkty", {"liczba": nowa_ilosc}, row['id'])
                db_post("sprzedaz", {"produkt_id": int(row['id']), "ilosc": ile, "suma": suma, "data": datetime.now().isoformat()})
                log("SPRZEDAŻ", f"{ile}x {wybrany}")
                st.success("Sprzedano!")
                st.rerun()
            else: st.error("Za mało towaru!")

# --- KATEGORIE ---
elif menu == "📂 Kategorie":
    st.title("Kategorie")
    nowa_kat = st.text_input("Nazwa kategorii")
    if st.button("Dodaj"):
        db_post("kategoria", {"nazwa": nowa_kat})
        log("KAT_DODAJ", nowa_kat)
        st.rerun()
    
    kats = db_get("kategoria")
    if kats: st.table(pd.DataFrame(kats))

# --- HISTORIA ---
elif menu == "📜 Historia":
    st.title("Dziennik")
    logs = db_get("dziennik", "order=id.desc")
    if logs: st.dataframe(pd.DataFrame(logs))
