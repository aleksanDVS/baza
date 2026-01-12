import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

# --- 1. KONFIGURACJA & POŁĄCZENIE ---
st.set_page_config(page_title="Sklep Magazynier Pro", layout="wide", page_icon="🧾")

# Initialize Supabase client
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. FUNKCJE POMOCNICZE (Supabase) ---

def zapisz_w_dzienniku(akcja, szczegoly):
    data = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "akcja": akcja,
        "szczegoly": szczegoly
    }
    supabase.table("dziennik").insert(data).execute()

def generuj_paragon(nazwa_p, ile, cena_jedn, suma):
    data_sprz = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
====================================
        POTWIERDZENIE SPRZEDAŻY
====================================
Data: {data_sprz}
------------------------------------
Produkt:    {nazwa_p}
Ilość:      {ile} szt.
Cena jedn.: {cena_jedn:.2f} zł
------------------------------------
SUMA:        {suma:.2f} zł
====================================
Dziękujemy za zakupy!
"""

# --- 3. NAWIGACJA ---
st.sidebar.title("🏢 Menu Główne")
menu = st.sidebar.radio("Wybierz moduł:", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "📜 Historia Operacji"])

# --- 4. MODUŁY ---

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki i Bilans")
    
    # Pobieranie danych z Supabase
    res_p = supabase.table("produkty").select("*, kategoria(nazwa)").execute()
    res_s = supabase.table("sprzedaz").select("*, produkty(nazwa)").execute()
    
    df_p = pd.DataFrame(res_p.data)
    df_s = pd.DataFrame(res_s.data)

    if not df_p.empty:
        # Re-format category name from join
        df_p['kategoria_nazwa'] = df_p['kategoria'].apply(lambda x: x['nazwa'] if x else "Brak")
        
        total_income = df_s['suma'].sum() if not df_s.empty else 0
        total_stock = df_p['liczba'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Całkowity Przychód", f"{total_income:,.2f} zł")
        c2.metric("W magazynie (szt.)", int(total_stock))

        st.plotly_chart(px.pie(df_p, values='liczba', names='kategoria_nazwa', title="Zapas wg kategorii"), use_container_width=True)
    else:
        st.info("Baza jest pusta.")

# --- MAGAZYN ---
elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    res_kat = supabase.table("kategoria").select("*").execute()
    df_kat = pd.DataFrame(res_kat.data)

    with st.expander("➕ Dodaj nowy produkt"):
        if not df_kat.empty:
            with st.form("add_p", clear_on_submit=True):
                n = st.text_input("Nazwa produktu")
                k_id = st.selectbox("Kategoria", df_kat['id'].tolist(), format_func=lambda x: df_kat[df_kat['id']==x]['nazwa'].values[0])
                l = st.number_input("Ilość", min_value=1)
                p = st.number_input("Cena", min_value=0.0)
                
                if st.form_submit_button("Zapisz"):
                    supabase.table("produkty").insert({"nazwa": n, "liczba": l, "cena": p, "kategoria_id": k_id}).execute()
                    zapisz_w_dzienniku("DODANIE", f"Dodano produkt: {n}")
                    st.success("Produkt dodany!")
                    st.rerun()

    res_v = supabase.table("produkty").select("id, nazwa, liczba, cena, kategoria(nazwa)").execute()
    st.dataframe(res_v.data, use_container_width=True)

# --- SPRZEDAŻ ---
elif menu == "💸 Sprzedaż":
    st.title("Punkt Sprzedaży")
    res_stock = supabase.table("produkty").select("*").gt("liczba", 0).execute()
    df_stock = pd.DataFrame(res_stock.data)

    if not df_stock.empty:
        with st.form("sale_form"):
            prod_id = st.selectbox("Produkt", df_stock['id'].tolist(), format_func=lambda x: df_stock[df_stock['id']==x]['nazwa'].values[0])
            ile = st.number_input("Ilość", min_value=1, step=1)
            confirm = st.form_submit_button("Potwierdź Sprzedaż")

            if confirm:
                row = df_stock[df_stock['id'] == prod_id].iloc[0]
                if ile <= row['liczba']:
                    suma = ile * row['cena']
                    # Update Stock
                    supabase.table("produkty").update({"liczba": int(row['liczba'] - ile)}).eq("id", prod_id).execute()
                    # Insert Sale
                    supabase.table("sprzedaz").insert({"produkt_id": prod_id, "ilosc": ile, "suma": suma, "data": datetime.now().isoformat()}).execute()
                    
                    zapisz_w_dzienniku("SPRZEDAŻ", f"Sprzedano {ile}x {row['nazwa']}")
                    st.session_state.paragon_data = generuj_paragon(row['nazwa'], ile, row['cena'], suma)
                    st.session_state.sukces = True
                else:
                    st.error("Brak wystarczającej ilości!")

        if st.session_state.get('sukces'):
            st.code(st.session_state.paragon_data)
            if st.button("Nowa transakcja"):
                st.session_state.sukces = False
                st.rerun()

# --- KATEGORIE ---
elif menu == "📂 Kategorie":
    st.title("Kategorie")
    nowa = st.text_input("Nowa kategoria")
    if st.button("Dodaj"):
        supabase.table("kategoria").insert({"nazwa": nowa}).execute()
        st.rerun()
    
    res = supabase.table("kategoria").select("*").execute()
    st.table(res.data)

# --- HISTORIA ---
elif menu == "📜 Historia Operacji":
    st.title("Logi")
    res_h = supabase.table("dziennik").select("*").order("id", desc=True).execute()
    st.dataframe(res_h.data, use_container_width=True)
