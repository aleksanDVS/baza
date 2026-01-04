import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="Sklep Magazynier Pro", layout="wide", page_icon="⚙️")

# --- BAZA DANYCH ---
def get_connection():
    conn = sqlite3.connect('sklep_final.db', check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
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
menu = st.sidebar.radio("Nawigacja", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "⚙️ Zarządzanie"])

# --- MODUŁ 1: DASHBOARD (NOWE STATYSTYKI) ---
if menu == "📊 Dashboard":
    st.title("Statystyki i Bilans")

    # 1. Pobranie danych o produktach i sprzedaży
    df_p = pd.read_sql_query("SELECT id, nazwa, liczba, cena FROM produkty", conn)
    df_s = pd.read_sql_query("SELECT produkt_id, ilosc FROM sprzedaz", conn)

    if not df_p.empty:
        # Obliczanie ile sprzedano każdego produktu
        sprzedane_suma = df_s.groupby('produkt_id')['ilosc'].sum().reset_index()
        sprzedane_suma.columns = ['id', 'Sprzedano']

        # Łączenie danych (Bilans)
        bilans = pd.merge(df_p, sprzedane_suma, on='id', how='left').fillna(0)
        bilans['Sprzedano'] = bilans['Sprzedano'].astype(int)
        
        # Obliczenie stanu początkowego (ile było = obecny stan + to co sprzedano)
        bilans['Łącznie było'] = bilans['liczba'] + bilans['Sprzedano']
        bilans = bilans.rename(columns={'nazwa': 'Produkt', 'liczba': 'Zostało (Stan)'})

        # Wyświetlenie metryk ogólnych
        total_income = pd.read_sql_query("SELECT SUM(suma) FROM sprzedaz", conn).iloc[0,0] or 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Całkowity Przychód", f"{total_income:,.2f} zł")
        c2.metric("Produkty w magazynie", bilans['Zostało (Stan)'].sum())
        c3.metric("Suma sprzedanych sztuk", bilans['Sprzedano'].sum())

        st.divider()
        
        # --- TABELA BILANSU ---
        st.subheader("📋 Pełny Bilans Towarowy")
        st.write("Zestawienie: ile wprowadzono, ile sprzedano i ile aktualnie znajduje się w magazynie.")
        
        # Wyświetlamy najważniejsze kolumny
        st.dataframe(
            bilans[['Produkt', 'Łącznie było', 'Sprzedano', 'Zostało (Stan)']], 
            use_container_width=True, 
            hide_index=True
        )

        # Wykres porównawczy
        st.subheader("📈 Wykres Ruchu Towarów")
        fig = px.bar(bilans, x='Produkt', y=['Sprzedano', 'Zostało (Stan)'], 
                     title="Proporcja Sprzedaży do Zapasów",
                     barmode='group',
                     color_discrete_map={'Sprzedano': '#EF553B', 'Zostało (Stan)': '#00CC96'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Baza produktów jest pusta.")

# --- POZOSTAŁE MODUŁY (Magazyn, Sprzedaż, Kategorie, Zarządzanie - pozostają jak w v4.5) ---
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
    st.subheader("Aktualny stan")
    df_view = pd.read_sql_query("SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id", conn)
    st.dataframe(df_view, use_container_width=True, hide_index=True)

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

elif menu == "📂 Kategorie":
    st.title("Kategorie")
    with st.form("add_k"):
        nowa_k = st.text_input("Nowa kategoria")
        if st.form_submit_button("Dodaj"):
            conn.cursor().execute("INSERT INTO kategoria (nazwa) VALUES (?)", (nowa_k,))
            conn.commit()
            st.rerun()
    st.table(pd.read_sql_query("SELECT * FROM kategoria", conn))

elif menu == "⚙️ Zarządzanie":
    st.title("Usuwanie danych")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        st.subheader("🗑️ Usuń Produkt")
        df_p_del = pd.read_sql_query("SELECT id, nazwa FROM produkty", conn)
        if not df_p_del.empty:
            p_to_del = st.selectbox("Wybierz produkt", df_p_del['nazwa'].tolist())
            if st.button("USUŃ PRODUKT", type="primary"):
                pid = df_p_del[df_p_del['nazwa'] == p_to_del]['id'].values[0]
                conn.cursor().execute("DELETE FROM produkty WHERE id = ?", (int(pid),))
                conn.commit()
                st.rerun()
    with col_u2:
        st.subheader("🗑️ Usuń Kategorię")
        df_k_del = pd.read_sql_query("SELECT id, nazwa FROM kategoria", conn)
        if not df_k_del.empty:
            k_to_del = st.selectbox("Wybierz kategorię", df_k_del['nazwa'].tolist())
            if st.button("USUŃ KATEGORIĘ", type="primary"):
                kid = df_k_del[df_k_del['nazwa'] == k_to_del]['id'].values[0]
                conn.cursor().execute("DELETE FROM kategoria WHERE id = ?", (int(kid),))
                conn.commit()
                st.rerun()

conn.close()
