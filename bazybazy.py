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

# --- NAWIGACJA ---
st.sidebar.title("🏢 Menu Główne")
menu = st.sidebar.radio("Wybierz moduł:", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "⚙️ Zarządzanie"])

# --- MODUŁ 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki, Bilans i Wykresy")

    # Pobieranie danych z bazy
    query_p = '''SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria 
                 FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id'''
    df_p = pd.read_sql_query(query_p, conn)
    df_s = pd.read_sql_query("SELECT produkt_id, ilosc, suma FROM sprzedaz", conn)

    if not df_p.empty:
        # Obliczenia do bilansu
        sprzedane_suma = df_s.groupby('produkt_id')['ilosc'].sum().reset_index()
        sprzedane_suma.columns = ['id', 'Sprzedano']
        bilans = pd.merge(df_p, sprzedane_suma, on='id', how='left').fillna(0)
        bilans['Sprzedano'] = bilans['Sprzedano'].astype(int)
        bilans['Łącznie było'] = bilans['liczba'] + bilans['Sprzedano']

        # 1. METRYKI
        total_income = df_s['suma'].sum() if not df_s.empty else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Całkowity Przychód", f"{total_income:,.2f} zł")
        c2.metric("Produkty w magazynie (szt.)", int(bilans['liczba'].sum()))
        c3.metric("Suma sprzedanych (szt.)", int(bilans['Sprzedano'].sum()))

        st.divider()

        # 2. LEGENDA SZCZEGÓŁOWA
        st.subheader("📝 Szczegółowa legenda sprzedaży")
        col_leg1, col_leg2 = st.columns(2)
        bilans_sorted = bilans.sort_values(by='Sprzedano', ascending=False).reset_index(drop=True)
        
        for i, row in bilans_sorted.iterrows():
            target_col = col_leg1 if i % 2 == 0 else col_leg2
            target_col.write(f"🔹 **{row['nazwa']}**: sprzedano **{row['Sprzedano']}** szt. (zostało: {row['liczba']})")

        st.divider()

        # 3. WYKRESY (Przywrócone!)
        st.subheader("📈 Wizualizacja Danych")
        col_graph1, col_graph2 = st.columns(2)

        with col_graph1:
            # Wykres kołowy - Udział kategorii
            fig_pie = px.pie(bilans, values='liczba', names='kategoria', 
                             title="Rozkład zapasów wg kategorii",
                             hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_graph2:
            # Wykres słupkowy - Bilans produktu
            fig_bar = px.bar(bilans, x='nazwa', y=['Sprzedano', 'liczba'], 
                             title="Porównanie: Sprzedaż vs Stan",
                             labels={'value': 'Ilość sztuk', 'variable': 'Status'},
                             barmode='group',
                             color_discrete_map={'Sprzedano': '#FFA15A', 'liczba': '#636EFA'})
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        
        # 4. TABELA BILANSOWA
        st.subheader("📋 Tabela Bilansowa")
        st.dataframe(bilans[['nazwa', 'kategoria', 'Łącznie było', 'Sprzedano', 'liczba']], 
                     column_config={"nazwa": "Produkt", "liczba": "Zostało w magazynie"},
                     use_container_width=True, hide_index=True)
    else:
        st.info("Baza produktów jest pusta. Dodaj dane, aby zobaczyć analizę.")

# --- POZOSTAŁE MODUŁY (Magazyn, Sprzedaż, Kategorie, Zarządzanie) ---
# (KOD POZOSTAJE TAKI SAM JAK W POPRZEDNIEJ WERSJI)
elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    df_kat = pd.read_sql_query("SELECT * FROM kategoria", conn)
    with st.expander("➕ Dodaj nowy produkt"):
        if not df_kat.empty:
            with st.form("add_p", clear_on_submit=True):
                n = st.text_input("Nazwa produktu")
                k = st.selectbox("Kategoria", df_kat['nazwa'].tolist())
                c1, c2 = st.columns(2)
                l = c1.number_input("Ilość", min_value=1)
                p = c2.number_input("Cena", min_value=0.0)
                if st.form_submit_button("Zapisz produkt"):
                    kid = df_kat[df_kat['nazwa'] == k]['id'].values[0]
                    conn.cursor().execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?,?,?,?)", (n,l,p,int(kid)))
                    conn.commit()
                    st.rerun()
    df_view = pd.read_sql_query("SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id", conn)
    st.dataframe(df_view, use_container_width=True, hide_index=True)

elif menu == "💸 Sprzedaż":
    st.title("Punkt Sprzedaży")
    df_stock = pd.read_sql_query("SELECT id, nazwa, liczba, cena FROM produkty WHERE liczba > 0", conn)
    if not df_stock.empty:
        with st.form("sale_form"):
            prod = st.selectbox("Wybierz produkt", df_stock['nazwa'].tolist())
            ile = st.number_input("Ilość", min_value=1)
            if st.form_submit_button("Sprzedaj"):
                row = df_stock[df_stock['nazwa'] == prod].iloc[0]
                if ile <= row['liczba']:
                    suma = ile * row['cena']
                    cur = conn.cursor()
                    cur.execute("UPDATE produkty SET liczba = liczba - ? WHERE id = ?", (ile, int(row['id'])))
                    cur.execute("INSERT INTO sprzedaz (data, produkt_id, ilosc, suma) VALUES (?,?,?,?)", 
                                (datetime.now().strftime("%Y-%m-%d"), int(row['id']), ile, suma))
                    conn.commit()
                    st.success(f"Sprzedano! Zysk: {suma:.2f} zł")
                    st.rerun()

elif menu == "📂 Kategorie":
    st.title("Kategorie")
    with st.form("add_k"):
        nowa_k = st.text_input("Nazwa nowej kategorii")
        if st.form_submit_button("Dodaj"):
            conn.cursor().execute("INSERT INTO kategoria (nazwa) VALUES (?)", (nowa_k,))
            conn.commit()
            st.rerun()
    st.table(pd.read_sql_query("SELECT nazwa FROM kategoria", conn))

elif menu == "⚙️ Zarządzanie":
    st.title("Usuwanie danych")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        st.subheader("Usuń Produkt")
        df_p_del = pd.read_sql_query("SELECT id, nazwa FROM produkty", conn)
        if not df_p_del.empty:
            p_to_del = st.selectbox("Wybierz produkt", df_p_del['nazwa'].tolist())
            if st.button("USUŃ"):
                pid = df_p_del[df_p_del['nazwa'] == p_to_del]['id'].values[0]
                conn.cursor().execute("DELETE FROM produkty WHERE id = ?", (int(pid),))
                conn.commit()
                st.rerun()
    with col_u2:
        st.subheader("Usuń Kategorię")
        df_k_del = pd.read_sql_query("SELECT id, nazwa FROM kategoria", conn)
        if not df_k_del.empty:
            k_to_del = st.selectbox("Wybierz kategorię", df_k_del['nazwa'].tolist())
            if st.button("USUŃ KATEGORIĘ"):
                kid = df_k_del[df_k_del['nazwa'] == k_to_del]['id'].values[0]
                conn.cursor().execute("DELETE FROM kategoria WHERE id = ?", (int(kid),))
                conn.commit()
                st.rerun()

conn.close()
