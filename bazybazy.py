import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="Sklep Magazynier Pro", layout="wide", page_icon="📊")

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

# --- NAWIGACJA (Musi być przed instrukcjami if!) ---
st.sidebar.title("🏢 Nawigacja")
menu = st.sidebar.radio("Wybierz moduł:", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "⚙️ Zarządzanie"])

# --- MODUŁ 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki i Bilans")

    # Pobieranie danych
    df_p = pd.read_sql_query("SELECT id, nazwa, liczba, cena FROM produkty", conn)
    df_s = pd.read_sql_query("SELECT produkt_id, ilosc, suma FROM sprzedaz", conn)

    if not df_p.empty:
        # Obliczenia bilansu
        sprzedane_suma = df_s.groupby('produkt_id')['ilosc'].sum().reset_index()
        sprzedane_suma.columns = ['id', 'Sprzedano']
        
        bilans = pd.merge(df_p, sprzedane_suma, on='id', how='left').fillna(0)
        bilans['Sprzedano'] = bilans['Sprzedano'].astype(int)
        bilans['Łącznie było'] = bilans['liczba'] + bilans['Sprzedano']

        # GŁÓWNE METRYKI
        total_income = df_s['suma'].sum() if not df_s.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Całkowity Przychód", f"{total_income:,.2f} zł")
        c2.metric("Produkty w magazynie", int(bilans['liczba'].sum()))
        c3.metric("Suma sprzedanych sztuk", int(bilans['Sprzedano'].sum()))

        st.divider()

        # --- TWOJA LEGENDA (Wyszczególnienie każdego produktu) ---
        st.subheader("📝 Legenda sprzedaży (szczegóły produktów)")
        
        col_leg1, col_leg2 = st.columns(2)
        bilans_sorted = bilans.sort_values(by='Sprzedano', ascending=False).reset_index()
        
        for i, row in bilans_sorted.iterrows():
            target_col = col_leg1 if i % 2 == 0 else col_leg2
            target_col.write(f"🔹 **{row['nazwa']}**: sprzedano **{row['Sprzedano']}** szt. (zostało: {row['liczba']})")

        st.divider()
        
        # Wykres i Tabela
        st.subheader("📋 Bilans Towarowy (Tabela)")
        st.dataframe(bilans[['nazwa', 'Łącznie było', 'Sprzedano', 'liczba']], 
                     column_config={"nazwa": "Produkt", "liczba": "Zostało (Obecnie)"},
                     use_container_width=True, hide_index=True)
    else:
        st.info("Baza produktów jest pusta. Dodaj towary, aby zobaczyć statystyki.")

# --- MODUŁ 2: MAGAZYN ---
elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    df_kat = pd.read_sql_query("SELECT * FROM kategoria", conn)
    
    with st.expander("➕ Dodaj nowy produkt"):
        if not df_kat.empty:
            with st.form("add_p", clear_on_submit=True):
                n = st.text_input("Nazwa produktu")
                k = st.selectbox("Kategoria", df_kat['nazwa'].tolist())
                c1, c2 = st.columns(2)
                l = c1.number_input("Ilość początkowa", min_value=1)
                p = c2.number_input("Cena jednostkowa", min_value=0.0)
                if st.form_submit_button("Zapisz produkt"):
                    kid = df_kat[df_kat['nazwa'] == k]['id'].values[0]
                    conn.cursor().execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?,?,?,?)", (n,l,p,int(kid)))
                    conn.commit()
                    st.success(f"Dodano: {n}")
                    st.rerun()
        else:
            st.warning("Najpierw dodaj kategorię!")

    st.subheader("Aktualny stan magazynowy")
    df_view = pd.read_sql_query("SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id", conn)
    st.dataframe(df_view, use_container_width=True, hide_index=True)

# --- MODUŁ 3: SPRZEDAŻ ---
elif menu == "💸 Sprzedaż":
    st.title("Punkt Sprzedaży")
    df_stock = pd.read_sql_query("SELECT id, nazwa, liczba, cena FROM produkty WHERE liczba > 0", conn)
    
    if not df_stock.empty:
        with st.form("sale_form", clear_on_submit=True):
            prod = st.selectbox("Wybierz produkt", df_stock['nazwa'].tolist())
            ile = st.number_input("Ilość sprzedanych sztuk", min_value=1)
            if st.form_submit_button("Potwierdź Sprzedaż"):
                row = df_stock[df_stock['nazwa'] == prod].iloc[0]
                if ile <= row['liczba']:
                    suma = ile * row['cena']
                    cur = conn.cursor()
                    cur.execute("UPDATE produkty SET liczba = liczba - ? WHERE id = ?", (ile, int(row['id'])))
                    cur.execute("INSERT INTO sprzedaz (data, produkt_id, ilosc, suma) VALUES (?,?,?,?)", 
                                (datetime.now().strftime("%Y-%m-%d"), int(row['id']), ile, suma))
                    conn.commit()
                    st.success(f"Sprzedano {ile}x {prod}. Zysk: {suma:.2f} zł")
                    st.rerun()
                else:
                    st.error("Brak wystarczającej ilości towaru!")
    else:
        st.warning("Brak towaru na sprzedaż.")

# --- MODUŁ 4: KATEGORIE ---
elif menu == "📂 Kategorie":
    st.title("Kategorie")
    with st.form("add_k", clear_on_submit=True):
        nowa_k = st.text_input("Nazwa nowej kategorii")
        if st.form_submit_button("Dodaj"):
            if nowa_k:
                try:
                    conn.cursor().execute("INSERT INTO kategoria (nazwa) VALUES (?)", (nowa_k,))
                    conn.commit()
                    st.rerun()
                except:
                    st.error("Taka kategoria już istnieje.")
    st.table(pd.read_sql_query("SELECT nazwa FROM kategoria", conn))

# --- MODUŁ 5: ZARZĄDZANIE ---
elif menu == "⚙️ Zarządzanie":
    st.title("Usuwanie danych")
    st.warning("Pamiętaj: usunięcie kategorii usuwa wszystkie przypisane do niej produkty!")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        st.subheader("Usuń Produkt")
        df_p_del = pd.read_sql_query("SELECT id, nazwa FROM produkty", conn)
        if not df_p_del.empty:
            p_to_del = st.selectbox("Wybierz produkt", df_p_del['nazwa'].tolist(), key="del_p")
            if st.button("USUŃ PRODUKT", type="primary"):
                pid = df_p_del[df_p_del['nazwa'] == p_to_del]['id'].values[0]
                conn.cursor().execute("DELETE FROM produkty WHERE id = ?", (int(pid),))
                conn.commit()
                st.rerun()
                
    with col_u2:
        st.subheader("Usuń Kategorię")
        df_k_del = pd.read_sql_query("SELECT id, nazwa FROM kategoria", conn)
        if not df_k_del.empty:
            k_to_del = st.selectbox("Wybierz kategorię", df_k_del['nazwa'].tolist(), key="del_k")
            if st.button("USUŃ KATEGORIĘ", type="primary"):
                kid = df_k_del[df_k_del['nazwa'] == k_to_del]['id'].values[0]
                conn.cursor().execute("DELETE FROM kategoria WHERE id = ?", (int(kid),))
                conn.commit()
                st.rerun()

conn.close()
