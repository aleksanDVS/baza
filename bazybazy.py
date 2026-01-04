import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="Sklep & Magazyn Pro", layout="wide", page_icon="💰")

# --- STYLE CSS ---
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.1);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 15px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BAZA DANYCH ---
def get_connection():
    return sqlite3.connect('sklep_v4.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS kategoria (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT UNIQUE)')
    cur.execute('''CREATE TABLE IF NOT EXISTS produkty (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT, liczba INTEGER, 
                    cena REAL, kategoria_id INTEGER, FOREIGN KEY(kategoria_id) REFERENCES kategoria(id))''')
    # NOWA TABELA: Sprzedaż
    cur.execute('''CREATE TABLE IF NOT EXISTS sprzedaz (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, produkt_id INTEGER, 
                    ilosc INTEGER, suma REAL, FOREIGN KEY(produkt_id) REFERENCES produkty(id))''')
    conn.commit()
    return conn

conn = init_db()

# --- FUNKCJE POMOCNICZE ---
def get_status(ilosc):
    if ilosc > 10: return "🟢 Dostępny"
    if ilosc > 0: return "🟡 Niski stan"
    return "🔴 Brak"

# --- NAWIGACJA ---
menu = st.sidebar.radio("Menu", ["📊 Analiza Sprzedaży", "📦 Magazyn", "💸 Punkt Sprzedaży", "📂 Kategorie"])

# --- MODUŁ 1: DASHBOARD (Z ROZBUDOWANĄ ANALIZĄ) ---
if menu == "📊 Analiza Sprzedaży":
    st.title("Panel Analityczny")
    
    # Pobieranie danych o sprzedaży
    query_sales = '''SELECT s.data, p.nazwa, s.ilosc, s.suma 
                     FROM sprzedaz s JOIN produkty p ON s.produkt_id = p.id'''
    df_sales = pd.read_sql_query(query_sales, conn)

    if not df_sales.empty:
        c1, c2 = st.columns(2)
        c1.metric("Całkowity Przychód", f"{df_sales['suma'].sum():,.2f} zł")
        c2.metric("Sprzedane Produkty", df_sales['ilosc'].sum())

        st.subheader("Historia Przychodów")
        df_sales['data'] = pd.to_datetime(df_sales['data'])
        fig_trend = px.line(df_sales.groupby('data')['suma'].sum().reset_index(), 
                            x='data', y='suma', title="Trend sprzedaży (PLN)")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Brak zarejestrowanej sprzedaży.")

# --- MODUŁ 2: MAGAZYN (ZE STATUSAMI) ---
elif menu == "📦 Magazyn":
    st.title("Stan Magazynowy")
    query = '''SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria 
               FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id'''
    df_p = pd.read_sql_query(query, conn)
    
    if not df_p.empty:
        # DODAWANIE STATUSÓW
        df_p['Status'] = df_p['liczba'].apply(get_status)
        st.dataframe(df_p[['Status', 'nazwa', 'liczba', 'cena', 'kategoria']], use_container_width=True)
    
    # Formularz dodawania (jak wcześniej)
    st.divider()
    st.subheader("Dodaj nowy produkt")
    df_k = pd.read_sql_query("SELECT * FROM kategoria", conn)
    with st.form("add_p"):
        name = st.text_input("Nazwa")
        cat = st.selectbox("Kategoria", df_k['nazwa'].tolist() if not df_k.empty else [])
        col1, col2 = st.columns(2)
        qty = col1.number_input("Ilość", min_value=1)
        prc = col2.number_input("Cena zakupu", min_value=0.0)
        if st.form_submit_button("Dodaj"):
            kid = df_k[df_k['nazwa'] == cat]['id'].values[0]
            conn.cursor().execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?,?,?,?)", 
                                 (name, qty, prc, int(kid)))
            conn.commit()
            st.rerun()

# --- MODUŁ 3: PUNKT SPRZEDAŻY (NOWOŚĆ) ---
elif menu == "💸 Punkt Sprzedaży":
    st.title("Nowa Sprzedaż")
    
    df_p = pd.read_sql_query("SELECT id, nazwa, liczba, cena FROM produkty WHERE liczba > 0", conn)
    
    if not df_p.empty:
        with st.form("sale_form"):
            prod_choice = st.selectbox("Wybierz produkt", options=df_p['nazwa'].tolist())
            ilosc_sell = st.number_input("Ilość do sprzedaży", min_value=1, step=1)
            
            if st.form_submit_button("Potwierdź Sprzedaż"):
                row = df_p[df_p['nazwa'] == prod_choice].iloc[0]
                if ilosc_sell <= row['liczba']:
                    suma = ilosc_sell * row['cena']
                    cur = conn.cursor()
                    # 1. Odejmij z magazynu
                    cur.execute("UPDATE produkty SET liczba = liczba - ? WHERE id = ?", (ilosc_sell, int(row['id'])))
                    # 2. Dodaj do tabeli sprzedaż
                    cur.execute("INSERT INTO sprzedaz (data, produkt_id, ilosc, suma) VALUES (?,?,?,?)",
                                (datetime.now().strftime("%Y-%m-%d"), int(row['id']), ilosc_sell, suma))
                    conn.commit()
                    st.success(f"Sprzedano {ilosc_sell}x {prod_choice} za {suma:.2f} zł")
                else:
                    st.error("Nie ma tyle towaru w magazynie!")
    else:
        st.warning("Brak produktów w magazynie do sprzedania.")

# --- MODUŁ 4: KATEGORIE ---
elif menu == "📂 Kategorie":
    st.title("Kategorie")
    new_k = st.text_input("Nazwa kategorii")
    if st.button("Dodaj"):
        conn.cursor().execute("INSERT INTO kategoria (nazwa) VALUES (?)", (new_k,))
        conn.commit()
        st.rerun()
    st.table(pd.read_sql_query("SELECT * FROM kategoria", conn))

conn.close()
