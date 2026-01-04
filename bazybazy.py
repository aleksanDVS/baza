import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="System Magazynowy Pro",
    page_icon="📦",
    layout="wide"
)

# --- CSS DLA LEPSZEGO WYGLĄDU (POPRAWIONE) ---
st.markdown("""
    <style>
    /* Elastyczny styl dla kafelków metric - dopasowuje się do tła */
    [data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.1);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 15px;
        border-radius: 10px;
    }
    /* Ukrycie indeksów w tabelach dla czystszego wyglądu */
    [data-testid="stTable"] td {
        text-align: left;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICJALIZACJA BAZY DANYCH ---
def get_connection():
    # check_same_thread=False jest wymagane dla Streamlit
    return sqlite3.connect('sklep_pro.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Tabela kategorii
    cur.execute('''CREATE TABLE IF NOT EXISTS kategoria 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT UNIQUE, opis TEXT)''')
    # Tabela produktów
    cur.execute('''CREATE TABLE IF NOT EXISTS produkty 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT, liczba INTEGER, 
                    cena REAL, kategoria_id INTEGER, 
                    FOREIGN KEY(kategoria_id) REFERENCES kategoria(id))''')
    # Tabela logów (Historia)
    cur.execute('''CREATE TABLE IF NOT EXISTS historia 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, akcja TEXT, szczegoly TEXT)''')
    conn.commit()
    return conn

def dodaj_log(akcja, szczegoly):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO historia (data, akcja, szczegoly) VALUES (?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), akcja, szczegoly))
    conn.commit()

# Inicjalizacja przy starcie
conn = init_db()

# --- PANEL BOCZNY (NAWIGACJA) ---
st.sidebar.title("🏢 Menu Główne")
menu = st.sidebar.radio("Przejdź do:", ["📊 Dashboard", "📦 Magazyn", "📂 Kategorie", "🕒 Historia"])

# --- MODUŁ 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki Magazynowe")
    
    # Pobieranie danych z Joinem
    query = '''SELECT p.nazwa as Produkt, p.liczba as Ilość, p.cena as Cena, k.nazwa as Kategoria 
               FROM produkty p 
               JOIN kategoria k ON p.kategoria_id = k.id'''
    df = pd.read_sql_query(query, conn)

    if not df.empty:
        df['Wartość'] = df['Ilość'] * df['Cena']
        
        # Metryki na górze
        c1, c2, c3 = st.columns(3)
        c1.metric("Wartość Magazynu", f"{df['Wartość'].sum():,.2f} zł")
        c2.metric("Liczba SKU", len(df))
        c3.metric("Stan Sztuk", int(df['Ilość'].sum()))

        st.divider()
        
        # Wykresy
        col_left, col_right = st.columns(2)
        with col_left:
            fig_pie = px.pie(df, values='Wartość', names='Kategoria', title="Udział kategorii w wartości")
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_right:
            # Alerty niskiego stanu
            st.subheader("⚠️ Niskie stany (< 5 szt.)")
            low_stock = df[df['Ilość'] < 5]
            if not low_stock.empty:
                st.dataframe(low_stock[['Produkt', 'Ilość']], hide_index=True, use_container_width=True)
            else:
                st.success("Wszystkie stany magazynowe są wystarczające.")
    else:
        st.info("Baza danych jest pusta. Dodaj kategorie i produkty w odpowiednich zakładkach.")

# --- MODUŁ 2: MAGAZYN ---
elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    
    # Pobieranie aktualnych kategorii
    df_k = pd.read_sql_query("SELECT * FROM kategoria", conn)
    
    tab_view, tab_add, tab_edit = st.tabs(["📋 Lista", "➕ Dodaj Nowy", "✏️ Edytuj/Usuń"])

    with tab_view:
        search = st.text_input("🔍 Szukaj produktu...")
        query = '''SELECT p.id as ID, p.nazwa as Nazwa, p.liczba as Ilość, p.cena as Cena, k.nazwa as Kategoria 
                   FROM produkty p 
                   JOIN kategoria k ON p.kategoria_id = k.id'''
        df_list = pd.read_sql_query(query, conn)
        if not df_list.empty:
            if search:
                df_list = df_list[df_list['Nazwa'].str.contains(search, case=False)]
            st.dataframe(df_list, use_container_width=True, hide_index=True)
        else:
            st.info("Brak produktów.")

    with tab_add:
        if not df_k.empty:
            with st.form("add_product_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                nazwa = col1.text_input("Nazwa produktu")
                kat = col2.selectbox("Kategoria", options=df_k['nazwa'].tolist())
                
                col3, col4 = st.columns(2)
                ile = col3.number_input("Ilość", min_value=0, step=1)
                pln = col4.number_input("Cena (zł)", min_value=0.0, format="%.2f")
                
                if st.form_submit_button("Dodaj do bazy"):
                    if nazwa:
                        kat_id = df_k[df_k['nazwa'] == kat]['id'].values[0]
                        cur = conn.cursor()
                        cur.execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?,?,?,?)", 
                                   (nazwa, ile, pln, int(kat_id)))
                        conn.commit()
                        dodaj_log("DODANIE", f"Dodano produkt: {nazwa}")
                        st.success(f"Dodano: {nazwa}")
                        st.rerun()
        else:
            st.error("Najpierw musisz dodać przynajmniej jedną kategorię!")

    with tab_edit:
        st.subheader("Aktualizacja lub Usuwanie")
        id_edit = st.number_input("Wpisz ID produktu do zmiany", min_value=1, step=1)
        new_q = st.number_input("Nowa ilość", min_value=0, step=1)
        
        c_e1, c_e2 = st.columns(2)
        if c_e1.button("Zaktualizuj ilość", use_container_width=True):
            cur = conn.cursor()
            cur.execute("UPDATE produkty SET liczba = ? WHERE id = ?", (new_q, id_edit))
            conn.commit()
            dodaj_log("EDYCJA", f"Zmieniono ilość ID {id_edit} na {new_q}")
            st.rerun()
            
        if c_e2.button("Usuń produkt z bazy", type="primary", use_container_width=True):
            cur = conn.cursor()
            cur.execute("DELETE FROM produkty WHERE id = ?", (id_edit,))
            conn.commit()
            dodaj_log("USUNIĘCIE", f"Usunięto produkt ID {id_edit}")
            st.rerun()

# --- MODUŁ 3: KATEGORIE ---
elif menu == "📂 Kategorie":
    st.title("Kategorie Produktów")
    
    with st.form("kat_form", clear_on_submit=True):
        st.subheader("Dodaj nową kategorię")
        kn = st.text_input("Nazwa kategorii")
        ko = st.text_area("Opis")
        if st.form_submit_button("Zapisz"):
            if kn:
                try:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO kategoria (nazwa, opis) VALUES (?,?)", (kn, ko))
                    conn.commit()
                    st.success(f"Kategoria {kn} została dodana.")
                    st.rerun()
                except:
                    st.error("Ta kategoria już istnieje w bazie!")

    st.divider()
    df_k_view = pd.read_sql_query("SELECT id, nazwa, opis FROM kategoria", conn)
    st.dataframe(df_k_view, use_container_width=True, hide_index=True)

# --- MODUŁ 4: HISTORIA ---
elif menu == "🕒 Historia":
    st.title("Dziennik Zdarzeń")
    df_h = pd.read_sql_query("SELECT data as Data, akcja as Akcja, szczegoly as Opis FROM historia ORDER BY id DESC", conn)
    if not df_h.empty:
        st.table(df_h)
        if st.button("Wyczyść historię logów"):
            conn.cursor().execute("DELETE FROM historia")
            conn.commit()
            st.rerun()
    else:
        st.info("Brak wpisów w historii.")

# Zamknięcie połączenia przy końcu działania skryptu
conn.close()
