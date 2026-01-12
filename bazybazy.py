import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. KONFIGURACJA SUPABASE ---
# Upewnij się, że URL kończy się na /rest/v1
SB_URL = "https://pfrgvpybklrmjnyttduo.supabase.co"
SB_KEY = "sb_publishable_TRb3wyGLDjmxQPXQ2AhtYw_uzmHiwnm"
HEADERS = {
    "apikey": SB_KEY,
    "Authorization": f"Bearer {SB_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# --- 2. FUNKCJE API ---
def db_get(table, params=""):
    try:
        r = requests.get(f"{SB_URL}/{table}?{params}", headers=HEADERS)
        return r.json()
    except:
        return []

def db_post(table, data):
    requests.post(f"{SB_URL}/{table}", headers=HEADERS, json=data)

def db_patch(table, data, id_val):
    requests.patch(f"{SB_URL}/{table}?id=eq.{id_val}", headers=HEADERS, json=data)

def log(akcja, szczegoly):
    db_post("dziennik", {
        "data": datetime.now().isoformat(), 
        "akcja": akcja, 
        "szczegoly": szczegoly, 
        "uzytkownik": "Admin"
    })

# --- 3. UI ---
st.set_page_config(page_title="Magazyn Supabase", layout="wide")
menu = st.sidebar.radio("Menu", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "📜 Historia"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki")
    p_data = db_get("produkty", "select=*,kategoria(nazwa)")
    
    if isinstance(p_data, list) and len(p_data) > 0:
        df = pd.DataFrame(p_data)
        # Zabezpieczenie wyciągania nazwy kategorii z relacji
        df['kat_nazwa'] = df['kategoria'].apply(lambda x: x['nazwa'] if isinstance(x, dict) else "Brak")
        
        c1, c2 = st.columns(2)
        c1.metric("Produkty w bazie", len(df))
        c2.metric("Suma sztuk", int(df['liczba'].sum()))
        st.bar_chart(df.set_index('nazwa')['liczba'])
    else:
        st.info("Baza jest pusta. Dodaj produkty w zakładce Magazyn.")

# --- MAGAZYN ---
elif menu == "📦 Magazyn":
    st.title("Magazyn")
    kat_data = db_get("kategoria")
    df_k = pd.DataFrame(kat_data) if (isinstance(kat_data, list) and len(kat_data) > 0) else pd.DataFrame()

    with st.expander("Dodaj produkt"):
        n = st.text_input("Nazwa")
        k_name = st.selectbox("Kategoria", df_k['nazwa'].tolist() if not df_k.empty else [])
        l = st.number_input("Ilość", min_value=0)
        c = st.number_input("Cena", min_value=0.0)
        if st.button("Zapisz"):
            if not df_k.empty and n:
                k_id = df_k[df_k['nazwa'] == k_name]['id'].values[0]
                db_post("produkty", {"nazwa": n, "liczba": l, "cena": c, "kategoria_id": int(k_id)})
                log("DODANIE", f"Produkt: {n}")
                st.rerun()

    prods = db_get("produkty", "select=*,kategoria(nazwa)")
    if isinstance(prods, list) and len(prods) > 0:
        df_p = pd.DataFrame(prods)
        # Czyszczenie wyglądu tabeli dla użytkownika
        df_p['kategoria'] = df_p['kategoria'].apply(lambda x: x['nazwa'] if isinstance(x, dict) else "Brak")
        st.table(df_p[['id', 'nazwa', 'liczba', 'cena', 'kategoria']])

# --- SPRZEDAŻ ---
elif menu == "💸 Sprzedaż":
    st.title("Sprzedaż")
    prods = db_get("produkty", "liczba=gt.0")
    if isinstance(prods, list) and len(prods) > 0:
        df_s = pd.DataFrame(prods)
        wybrany = st.selectbox("Produkt", df_s['nazwa'].tolist())
        ile = st.number_input("Ile sztuk", min_value=1)
        if st.button("Sprzedaj"):
            row = df_s[df_s['nazwa'] == wybrany].iloc[0]
            if ile <= row['liczba']:
                nowa_ilosc = int(row['liczba'] - ile)
                suma = ile * float(row['cena'])
                db_patch("produkty", {"liczba": nowa_ilosc}, row['id'])
                db_post("sprzedaz", {
                    "produkt_id": int(row['id']), 
                    "ilosc": ile, 
                    "suma": suma, 
                    "data": datetime.now().isoformat()
                })
                log("SPRZEDAŻ", f"{ile}x {wybrany}")
                st.success(f"Sprzedano! Suma: {suma:.2f}")
                st.rerun()
            else: st.error("Za mało towaru!")
    else:
        st.warning("Brak produktów z ilością większą niż 0.")

# --- KATEGORIE ---
elif menu == "📂 Kategorie":
    st.title("Kategorie")
    nowa_kat = st.text_input("Nazwa kategorii")
    if st.button("Dodaj"):
        if nowa_kat:
            db_post("kategoria", {"nazwa": nowa_kat})
            log("KAT_DODAJ", nowa_kat)
            st.rerun()
    
    kats = db_get("kategoria")
    if isinstance(kats, list) and len(kats) > 0:
        st.table(pd.DataFrame(kats))

# --- HISTORIA ---
elif menu == "📜 Historia":
    st.title("Dziennik")
    logs = db_get("dziennik", "order=id.desc")
    if isinstance(logs, list) and len(logs) > 0:
        st.dataframe(pd.DataFrame(logs), use_container_width=True)
