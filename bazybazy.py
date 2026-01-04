import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="Sklep Magazynier Pro", layout="wide", page_icon="⚙️")

# --- STYLE CSS ---
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.1);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 15px;
        border-radius: 10px;
    }
    .stButton>button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- BAZA DANYCH ---
def get_connection():
    conn = sqlite3.connect('sklep_final.db', check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON") # Włączenie wsparcia dla kluczy obcych
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS kategoria (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT UNIQUE)')
    cur.execute('''CREATE TABLE IF NOT EXISTS produkty (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT, liczba INTEGER, 
                    cena REAL, kategoria_id INTEGER, 
                    FOREIGN KEY(kategoria_id) REFERENCES kategoria(id) ON DELETE CASCADE)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sprzedaz (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, produkt_id INTEGER, 
                    ilosc INTEGER, suma REAL)''')
    conn.commit()
    return conn

conn = init_db()

# --- NAWIGACJA ---
menu = st.sidebar.radio("Nawigacja", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "⚙️ Usuwanie i Porządki"])

# --- MODUŁ 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki Sklepu")
    df_p = pd.read_sql_query("SELECT p.nazwa, p.liczba, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id", conn)
    df_s = pd.read_sql_query("SELECT suma FROM sprzedaz", conn)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Suma sprzedaży", f"{df_s['suma'].sum():,.2f} zł")
    c2.metric("Wartość magazynu", f"{(df_p['liczba'] * df_p['cena']).sum():,.2f} zł")
    c3.metric("Liczba produktów", len(df_p))
    
    if not df_p.empty:
        fig = px.pie(df_p, values='liczba', names='kategoria', title="Ilość towaru wg kategorii")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 2: MAGAZYN ---
elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    df_kat = pd.read_sql_query("SELECT * FROM kategoria", conn)
    
    with st.expander("➕ Dodaj nowy produkt"):
        if not df_kat.empty:
            with st.form("add_p"):
                n = st.text_input("Nazwa")
                k = st.selectbox("Kategoria", df_kat['nazwa'].tolist())
                c1, c2 = st.columns(2)
                l = c1.number_input("Ilość", min_value=1)
                p = c2.number_input("Cena", min_value=0.0)
                if st.form_submit_button("Zapisz"):
                    kid = df_kat[df_kat['nazwa'] == k]['id'].values[0]
                    conn.cursor().execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?,?,?,?)", (n,l,p,int(kid)))
                    conn.commit()
                    st.rerun()
        else: st.warning("Brak kategorii!")

    st.subheader("Aktualny stan")
    df_view = pd.read_sql_query("SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id", conn)
    st.dataframe(df_view, use_container_width=True, hide_index=True)

# --- MODUŁ 3: SPRZEDAŻ ---
elif menu == "💸 Sprzedaż":
    st.title("Punkt Sprzedaży")
    df_stock = pd.read_sql_query("SELECT id, nazwa, liczba, cena FROM produkty WHERE liczba > 0", conn)
    if not df_stock.empty:
        with st.form("sale"):
            prod = st.selectbox("Produkt", df_stock['nazwa'].tolist())
            ile = st.number_input("Ile sztuk", min_value=1)
            if st.form_submit_button("Sprzedaj"):
                row = df_stock[df_stock['nazwa'] == prod].iloc[0]
                if ile <= row['liczba']:
                    suma = ile * row['cena']
                    cur = conn.cursor()
                    cur.execute("UPDATE produkty SET liczba = liczba - ? WHERE id = ?", (ile, int(row['id'])))
                    cur.execute("INSERT INTO sprzedaz (data, produkt_id, ilosc, suma) VALUES (?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), int(row['id']), ile, suma))
                    conn.commit()
                    st.success(f"Sprzedano! Wartość: {suma} zł")
                    st.rerun()
                else: st.error("Za mało towaru!")

# --- MODUŁ 4: KATEGORIE ---
elif menu == "📂 Kategorie":
    st.title("Zarządzanie Kategoriami")
    with st.form("add_k"):
        nowa_k = st.text_input("Nowa kategoria")
        if st.form_submit_button("Dodaj"):
            conn.cursor().execute("INSERT INTO kategoria (nazwa) VALUES (?)", (nowa_k,))
            conn.commit()
            st.rerun()
    st.table(pd.read_sql_query("SELECT * FROM kategoria", conn))

# --- MODUŁ 5: USUWANIE (NOWOŚĆ) ---
elif menu == "⚙️ Usuwanie i Porządki":
    st.title("Usuwanie danych z bazy")
    
    col_u1, col_u2 = st.columns(2)
    
    with col_u1:
        st.subheader("🗑️ Usuń Produkt")
        df_p_del = pd.read_sql_query("SELECT id, nazwa FROM produkty", conn)
        if not df_p_del.empty:
            p_to_del = st.selectbox("Wybierz produkt do usunięcia", df_p_del['nazwa'].tolist())
            if st.button("USUŃ PRODUKT", type="primary"):
                pid = df_p_del[df_p_del['nazwa'] == p_to_del]['id'].values[0]
                conn.cursor().execute("DELETE FROM produkty WHERE id = ?", (int(pid),))
                conn.commit()
                st.success(f"Usunięto: {p_to_del}")
                st.rerun()
        else: st.info("Brak produktów")

    with col_u2:
        st.subheader("🗑️ Usuń Kategorię")
        df_k_del = pd.read_sql_query("SELECT id, nazwa FROM kategoria", conn)
        if not df_k_del.empty:
            k_to_del = st.selectbox("Wybierz kategorię", df_k_del['nazwa'].tolist())
            st.warning("⚠️ Usunięcie kategorii usunie również wszystkie produkty do niej przypisane!")
            if st.button("USUŃ KATEGORIĘ", type="primary"):
                kid = df_k_del[df_k_del['nazwa'] == k_to_del]['id'].values[0]
                conn.cursor().execute("DELETE FROM kategoria WHERE id = ?", (int(kid),))
                conn.commit()
                st.success(f"Usunięto kategorię i powiązane produkty")
                st.rerun()
        else: st.info("Brak kategorii")

conn.close()
