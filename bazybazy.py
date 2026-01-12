import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Magazynier Pro Cloud", layout="wide", page_icon="🧾")

# Connect to Supabase using Secrets
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd konfiguracji Secrets! Sprawdź ustawienia w Streamlit Cloud.")
    st.stop()

# --- 2. HELPER FUNCTIONS ---
def zapisz_dziennik(akcja, szczegoly):
    supabase.table("dziennik").insert({
        "data": datetime.now().isoformat(),
        "akcja": akcja, 
        "szczegoly": szczegoly
    }).execute()

# --- 3. NAVIGATION ---
menu = st.sidebar.radio("Nawigacja", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "📜 Historia"])

# --- 4. MODULES ---

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki i Bilans")
    
    # Fetch data
    res_p = supabase.table("produkty").select("*, kategoria(nazwa)").execute()
    res_s = supabase.table("sprzedaz").select("*, produkty(nazwa)").execute()
    
    df_p = pd.DataFrame(res_p.data)
    df_s = pd.DataFrame(res_s.data)

    if not df_p.empty:
        # Metrics
        total_income = df_s['suma'].sum() if not df_s.empty else 0
        total_stock = df_p['liczba'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Całkowity Przychód", f"{total_income:,.2f} zł")
        c2.metric("W magazynie (szt.)", int(total_stock))

        # Re-format category names for the chart
        df_p['kategoria_nazwa'] = df_p['kategoria'].apply(lambda x: x['nazwa'] if x else "Brak")
        
        st.divider()
        st.subheader("📈 Wizualizacja Zapasów")
        fig = px.pie(df_p, values='liczba', names='kategoria_nazwa', title="Zapas wg kategorii", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Baza danych jest pusta. Dodaj kategorie i produkty.")

# --- WAREHOUSE (MAGAZYN) ---
elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    
    res_kat = supabase.table("kategoria").select("*").execute()
    df_kat = pd.DataFrame(res_kat.data)

    if df_kat.empty:
        st.warning("Najpierw dodaj kategorię w zakładce 'Kategorie'!")
    else:
        with st.expander("➕ Dodaj nowy produkt"):
            with st.form("add_product", clear_on_submit=True):
                nazwa = st.text_input("Nazwa produktu")
                kat_id = st.selectbox("Kategoria", df_kat['id'].tolist(), 
                                      format_func=lambda x: df_kat[df_kat['id']==x]['nazwa'].values[0])
                c1, c2 = st.columns(2)
                ilosc = c1.number_input("Ilość", min_value=1)
                cena = c2.number_input("Cena", min_value=0.0)
                
                if st.form_submit_button("Zapisz w Bazie"):
                    supabase.table("produkty").insert({
                        "nazwa": nazwa, "liczba": ilosc, "cena": cena, "kategoria_id": kat_id
                    }).execute()
                    zapisz_dziennik("DODANIE", f"Dodano produkt: {nazwa}")
                    st.success(f"Dodano {nazwa} do chmury!")
                    st.rerun()

    # Display Stock
    res = supabase.table("produkty").select("id, nazwa, liczba, cena, kategoria(nazwa)").execute()
    if res.data:
        df_view = pd.DataFrame(res.data)
        # Flatten the category name
        df_view['kategoria'] = df_view['kategoria'].apply(lambda x: x['nazwa'] if x else "Brak")
        st.subheader("Aktualny Stan Magazynowy")
        st.dataframe(df_view[['nazwa', 'kategoria', 'liczba', 'cena']], use_container_width=True)

# --- SALES (SPRZEDAŻ) ---
elif menu == "💸 Sprzedaż":
    st.title("Punkt Sprzedaży")
    res_p = supabase.table("produkty").select("*").gt("liczba", 0).execute()
    df_p = pd.DataFrame(res_p.data)

    if not df_p.empty:
        with st.form("sale"):
            p_id = st.selectbox("Wybierz produkt", df_p['id'].tolist(), 
                                format_func=lambda x: df_p[df_p['id']==x]['nazwa'].values[0])
            ile = st.number_input("Ilość sztuk", min_value=1, step=1)
            
            if st.form_submit_button("Potwierdź Sprzedaż"):
                row = df_p[df_p['id'] == p_id].iloc[0]
                if ile <= row['liczba']:
                    nowa_liczba = int(row['liczba'] - ile)
                    suma = ile * row['cena']
                    
                    # Update Stock and Record Sale
                    supabase.table("produkty").update({"liczba": nowa_liczba}).eq("id", p_id).execute()
                    supabase.table("sprzedaz").insert({"produkt_id": p_id, "ilosc": ile, "suma": suma}).execute()
                    
                    zapisz_dziennik("SPRZEDAŻ", f"Sprzedano {ile}x {row['nazwa']}")
                    st.success(f"Sprzedano! Wartość: {suma:.2f} zł")
                    st.rerun()
                else:
                    st.error(f"Brak wystarczającej ilości! Dostępne: {row['liczba']}")
    else:
        st.warning("Magazyn jest pusty!")

# --- CATEGORIES (KATEGORIE) ---
elif menu == "📂 Kategorie":
    st.title("Kategorie Produktów")
    with st.form("add_kat", clear_on_submit=True):
        nowa_kat = st.text_input("Nazwa nowej kategorii")
        if st.form_submit_button("Dodaj"):
            if nowa_kat:
                supabase.table("kategoria").insert({"nazwa": nowa_kat}).execute()
                zapisz_dziennik("KATEGORIA", f"Utworzono kategorię: {nowa_kat}")
                st.success("Dodano!")
                st.rerun()

    res = supabase.table("kategoria").select("*").execute()
    if res.data:
        st.table(pd.DataFrame(res.data)[['nazwa']])

# --- HISTORY ---
elif menu == "📜 Historia":
    st.title("Dziennik Operacji")
    res_h = supabase.table("dziennik").select("*").order("id", desc=True).execute()
    if res_h.data:
        st.dataframe(pd.DataFrame(res_h.data), use_container_width=True)
