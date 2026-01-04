import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# --- KONFIGURACJA ---
st.set_page_config(page_title="Sklep Magazynier Pro", layout="wide", page_icon="🧾")

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
    # NOWA TABELA: Logi systemowe
    cur.execute('''CREATE TABLE IF NOT EXISTS dziennik (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, akcja TEXT, szczegoly TEXT)''')
    conn.commit()
    return conn

# FUNKCJA DO ZAPISYWANIA W HISTORII
def zapisz_w_dzienniku(akcja, szczegoly):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO dziennik (data, akcja, szczegoly) VALUES (?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), akcja, szczegoly))
    conn.commit()

conn = init_db()

# --- FUNKCJA GENEROWANIA PARAGONU ---
def generuj_paragon(nazwa_p, ile, cena_jedn, suma):
    data_sprz = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    paragon = f"""
    ====================================
           POTWIERDZENIE SPRZEDAŻY
    ====================================
    Data: {data_sprz}
    ------------------------------------
    Produkt:    {nazwa_p}
    Ilość:      {ile} szt.
    Cena jedn.: {cena_jedn:.2f} zł
    ------------------------------------
    SUMA:       {suma:.2f} zł
    ====================================
    Dziękujemy za zakupy!
    """
    return paragon

# --- NAWIGACJA ---
st.sidebar.title("🏢 Menu Główne")
menu = st.sidebar.radio("Wybierz moduł:", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "⚙️ Zarządzanie", "📜 Historia Operacji"])

# --- MODUŁ 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki, Bilans i Wykresy")
    query_p = '''SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria 
                 FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id'''
    df_p = pd.read_sql_query(query_p, conn)
    df_s = pd.read_sql_query("SELECT s.data, p.nazwa, s.ilosc, s.suma FROM sprzedaz s JOIN produkty p ON s.produkt_id = p.id", conn)

    if not df_p.empty:
        sprzedane_suma = df_s.groupby('nazwa')['ilosc'].sum().reset_index()
        sprzedane_suma.columns = ['nazwa', 'Sprzedano']
        bilans = pd.merge(df_p, sprzedane_suma, on='nazwa', how='left').fillna(0)
        bilans['Sprzedano'] = bilans['Sprzedano'].astype(int)
        bilans['Łącznie było'] = bilans['liczba'] + bilans['Sprzedano']

        total_income = df_s['suma'].sum() if not df_s.empty else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Całkowity Przychód", f"{total_income:,.2f} zł")
        c2.metric("W magazynie (szt.)", int(bilans['liczba'].sum()))
        c3.metric("Sprzedano (szt.)", int(bilans['Sprzedano'].sum()))

        st.divider()
        st.subheader("📝 Szczegółowa legenda sprzedaży")
        col_leg1, col_leg2 = st.columns(2)
        bilans_sorted = bilans.sort_values(by='Sprzedano', ascending=False).reset_index(drop=True)
        for i, row in bilans_sorted.iterrows():
            target_col = col_leg1 if i % 2 == 0 else col_leg2
            target_col.write(f"🔹 **{row['nazwa']}**: sprzedano **{row['Sprzedano']}** szt. (zostało: {row['liczba']})")

        st.divider()
        st.subheader("📈 Wizualizacja Danych")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(px.pie(bilans, values='liczba', names='kategoria', title="Zapas wg kategorii", hole=0.4), use_container_width=True)
        with col_g2:
            st.plotly_chart(px.bar(bilans, x='nazwa', y=['Sprzedano', 'liczba'], title="Sprzedaż vs Stan", barmode='group'), use_container_width=True)
            
        st.subheader("🕒 Ostatnie transakcje")
        st.dataframe(df_s.tail(5), use_container_width=True, hide_index=True)
    else:
        st.info("Baza jest pusta.")

# --- MODUŁ 2: MAGAZYN ---
elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    df_kat = pd.read_sql_query("SELECT * FROM kategoria", conn)
    with st.expander("➕ Dodaj nowy produkt"):
        if not df_kat.empty:
            with st.form("add_p"):
                n = st.text_input("Nazwa produktu")
                k = st.selectbox("Kategoria", df_kat['nazwa'].tolist())
                c1, c2 = st.columns(2)
                l = c1.number_input("Ilość", min_value=1)
                p = c2.number_input("Cena", min_value=0.0)
                if st.form_submit_button("Zapisz"):
                    kid = df_kat[df_kat['nazwa'] == k]['id'].values[0]
                    conn.cursor().execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?,?,?,?)", (n,l,p,int(kid)))
                    conn.commit()
                    zapisz_w_dzienniku("DODANIE", f"Dodano produkt: {n} ({l} szt.)")
                    st.rerun()
    df_v = pd.read_sql_query("SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id", conn)
    st.dataframe(df_v, use_container_width=True, hide_index=True)

# --- MODUŁ 3: SPRZEDAŻ ---
elif menu == "💸 Sprzedaż":
    st.title("Punkt Sprzedaży")
    df_stock = pd.read_sql_query("SELECT id, nazwa, liczba, cena FROM produkty WHERE liczba > 0", conn)
    if not df_stock.empty:
        with st.form("sale_form"):
            prod = st.selectbox("Wybierz produkt", df_stock['nazwa'].tolist())
            ile = st.number_input("Ilość", min_value=1, step=1)
            confirm = st.form_submit_button("Potwierdź Sprzedaż")
            if confirm:
                row = df_stock[df_stock['nazwa'] == prod].iloc[0]
                if ile <= row['liczba']:
                    suma = ile * row['cena']
                    cur = conn.cursor()
                    cur.execute("UPDATE produkty SET liczba = liczba - ? WHERE id = ?", (ile, int(row['id'])))
                    cur.execute("INSERT INTO sprzedaz (data, produkt_id, ilosc, suma) VALUES (?,?,?,?)", 
                                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(row['id']), ile, suma))
                    conn.commit()
                    zapisz_w_dzienniku("SPRZEDAŻ", f"Sprzedano {ile}x {prod} za {suma:.2f} zł")
                    st.success(f"Sprzedano! Wartość: {suma:.2f} zł")
                    txt_paragon = generuj_paragon(prod, ile, row['cena'], suma)
                    st.download_button(label="📥 Pobierz Potwierdzenie (TXT)", data=txt_paragon, file_name=f"paragon_{datetime.now().strftime('%H%M%S')}.txt")
                else:
                    st.error("Brak towaru.")

# --- MODUŁ 4: KATEGORIE ---
elif menu == "📂 Kategorie":
    st.title("Kategorie")
    with st.form("add_k"):
        nk = st.text_input("Nazwa")
        if st.form_submit_button("Dodaj"):
            conn.cursor().execute("INSERT INTO kategoria (nazwa) VALUES (?)", (nk,))
            conn.commit()
            zapisz_w_dzienniku("KATEGORIA", f"Dodano kategorię: {nk}")
            st.rerun()
    st.table(pd.read_sql_query("SELECT * FROM kategoria", conn))

# --- MODUŁ 5: ZARZĄDZANIE ---
elif menu == "⚙️ Zarządzanie":
    st.title("Usuwanie")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        dp = pd.read_sql_query("SELECT nazwa FROM produkty", conn)
        if not dp.empty:
            p_del = st.selectbox("Produkt", dp['nazwa'].tolist())
            if st.button("Usuń Produkt"):
                conn.cursor().execute("DELETE FROM produkty WHERE nazwa = ?", (p_del,))
                conn.commit()
                zapisz_w_dzienniku("USUNIĘCIE", f"Usunięto produkt: {p_del}")
                st.rerun()
    with col_u2:
        dk = pd.read_sql_query("SELECT nazwa FROM kategoria", conn)
        if not dk.empty:
            k_del = st.selectbox("Kategoria", dk['nazwa'].tolist())
            if st.button("Usuń Kategorię"):
                conn.cursor().execute("DELETE FROM kategoria WHERE nazwa = ?", (k_del,))
                conn.commit()
                zapisz_w_dzienniku("USUNIĘCIE", f"Usunięto kategorię: {k_del}")
                st.rerun()

# --- MODUŁ 6: HISTORIA OPERACJI (NOWOŚĆ) ---
elif menu == "📜 Historia Operacji":
    st.title("📜 Dziennik zdarzeń systemowych")
    st.write("Tu zapisywane są wszystkie akcje wykonane w aplikacji.")
    
    df_dziennik = pd.read_sql_query("SELECT data as Data, akcja as Akcja, szczegoly as Opis FROM dziennik ORDER BY id DESC", conn)
    
    if not df_dziennik.empty:
        st.dataframe(df_dziennik, use_container_width=True, hide_index=True)
        if st.button("Wyczyść dziennik zdarzeń"):
            conn.cursor().execute("DELETE FROM dziennik")
            conn.commit()
            st.rerun()
    else:
        st.info("Dziennik jest jeszcze pusty.")

conn.close()
