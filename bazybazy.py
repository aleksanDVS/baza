import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# --- FUNKCJE BAZODANOWE ---
def get_connection():
    conn = sqlite3.connect('sklep.db', check_same_thread=False)
    return conn

def inicjalizuj_baze():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kategoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazwa TEXT NOT NULL,
            opis TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produkty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazwa TEXT NOT NULL,
            liczba INTEGER,
            cena REAL,
            kategoria_id INTEGER,
            FOREIGN KEY (kategoria_id) REFERENCES kategoria (id)
        )
    ''')
    conn.commit()
    return conn

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn v2.0", layout="wide")
conn = inicjalizuj_baze()

# --- CSS DLA LEPSZEGO WYGLĄDU ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("📦 System Zarządzania Sklepem (SQLite)")

# --- BOCZNY PANEL (Pobieranie kategorii do list wyboru) ---
def pobierz_kategorie():
    df_kat = pd.read_sql_query("SELECT * FROM kategoria", conn)
    return df_kat

# --- TABS ---
tab_stats, tab_add_p, tab_add_k, tab_manage = st.tabs([
    "📊 Dashboard", "🍎 Produkty", "📂 Kategorie", "⚙️ Administracja"
])

# --- TAB 1: DASHBOARD ---
with tab_stats:
    query = '''
        SELECT p.id, p.nazwa as Produkt, p.liczba as Ilość, p.cena as Cena, k.nazwa as Kategoria 
        FROM produkty p
        JOIN kategoria k ON p.kategoria_id = k.id
    '''
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        df['Wartość'] = df['Ilość'] * df['Cena']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Łączna wartość", f"{df['Wartość'].sum():,.2f} zł")
        c2.metric("Liczba pozycji", len(df))
        c3.metric("Stan magazynowy", int(df['Ilość'].sum()))
        
        col_l, col_r = st.columns(2)
        with col_l:
            fig1 = px.pie(df, values='Wartość', names='Kategoria', title="Udział wartościowy kategorii")
            st.plotly_chart(fig1, use_container_width=True)
        with col_r:
            fig2 = px.bar(df, x='Produkt', y='Ilość', color='Kategoria', title="Ilość produktów")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Baza jest pusta. Dodaj kategorie i produkty!")

# --- TAB 2: DODAWANIE PRODUKTÓW ---
with tab_add_p:
    st.header("Dodaj nowy produkt")
    df_k = pobierz_kategorie()
    
    if not df_k.empty:
        with st.form("form_produkt", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nazwa_p = col1.text_input("Nazwa produktu")
            kat_p = col2.selectbox("Wybierz kategorię", options=df_k['nazwa'].tolist())
            
            col3, col4 = st.columns(2)
            ilosc_p = col3.number_input("Ilość", min_value=0, step=1)
            cena_p = col4.number_input("Cena (zł)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("Zapisz produkt"):
                if nazwa_p:
                    id_kat = df_k[df_k['nazwa'] == kat_p]['id'].values[0]
                    cur = conn.cursor()
                    cur.execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?, ?, ?, ?)",
                                (nazwa_p, ilosc_p, cena_p, int(id_kat)))
                    conn.commit()
                    st.success(f"Dodano produkt: {nazwa_p}")
                    st.rerun()
    else:
        st.warning("Najpierw musisz dodać kategorię!")

# --- TAB 3: DODAWANIE KATEGORII ---
with tab_add_k:
    st.header("Zarządzaj kategoriami")
    with st.form("form_kat", clear_on_submit=True):
        n_kat = st.text_input("Nazwa nowej kategorii")
        o_kat = st.text_area("Opis")
        if st.form_submit_button("Dodaj kategorię"):
            if n_kat:
                cur = conn.cursor()
                cur.execute("INSERT INTO kategoria (nazwa, opis) VALUES (?, ?)", (n_kat, o_kat))
                conn.commit()
                st.success("Kategoria dodana!")
                st.rerun()
    
    st.subheader("Istniejące kategorie")
    st.table(df_k)

# --- TAB 4: ADMINISTRACJA ---
with tab_manage:
    st.header("Podgląd i usuwanie")
    df_all = pd.read_sql_query(query, conn) if not df_k.empty else pd.DataFrame()
    
    if not df_all.empty:
        st.dataframe(df_all, use_container_width=True, hide_index=True)
        
        id_do_usu_p = st.number_input("Podaj ID produktu do usunięcia", min_value=1, step=1)
        if st.button("Usuń wybrany produkt", type="primary"):
            cur = conn.cursor()
            cur.execute("DELETE FROM produkty WHERE id = ?", (id_do_usu_p,))
            conn.commit()
            st.rerun()
            
        st.divider()
        csv = df_all.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Pobierz raport CSV", csv, "magazyn.csv", "text/csv")
    else:
        st.info("Brak danych.")

conn.close()
