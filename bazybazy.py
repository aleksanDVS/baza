import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="System Magazynowy Pro", layout="wide")

# Bezpieczne pobieranie danych logowania
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd: Brak kluczy Supabase w st.secrets!")
    st.stop()

# --- FUNKCJE DO POBIERANIA DANYCH ---
def get_categories():
    try:
        res = supabase.table("kategoria").select("id, nazwa").execute()
        return {item['nazwa']: item['id'] for item in res.data}
    except:
        return {}

def get_products_df():
    try:
        # Pobieramy produkty wraz z nazwą kategorii
        res = supabase.table("produkty").select("id, nazwa, liczba, cena, kategoria(nazwa)").execute()
        if not res.data:
            return pd.DataFrame()
        
        # Przekształcenie danych do płaskiej tabeli (ważne przy Joinach w Supabase)
        data = []
        for item in res.data:
            data.append({
                "ID": item["id"],
                "Produkt": item["nazwa"],
                "Ilość": item["liczba"],
                "Cena (zł)": item["cena"],
                "Kategoria": item["kategoria"]["nazwa"] if item.get("kategoria") else "Nieprzypisany",
                "Wartość (zł)": item["liczba"] * item["cena"]
            })
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Błąd pobierania produktów: {e}")
        return pd.DataFrame()

# --- MENU GŁÓWNE ---
st.title("📦 System Zarządzania Magazynem")

tabs = st.tabs(["📊 Statystyki", "🛒 Produkty", "📂 Kategorie", "⚙️ Zarządzanie"])

# --- TAB: STATYSTYKI ---
with tabs[0]:
    df = get_products_df()
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Wartość magazynu", f"{df['Wartość (zł)'].sum():.2f} zł")
        c2.metric("Liczba produktów", len(df))
        c3.metric("Łączna ilość sztuk", df['Ilość'].sum())

        st.divider()
        col_left, col_right = st.columns(2)
        
        with col_left:
            fig = px.pie(df, values='Wartość (zł)', names='Kategoria', title="Podział wartości wg kategorii")
            st.plotly_chart(fig, use_container_width=True)
            
        with col_right:
            # Alert o niskim stanie
            low_stock = df[df['Ilość'] < 5]
            if not low_stock.empty:
                st.warning("⚠️ Produkty na wyczerpaniu (poniżej 5 sztuk):")
                st.dataframe(low_stock[['Produkt', 'Ilość']], hide_index=True)
    else:
        st.info("Brak danych do wyświetlenia statystyk.")

# --- TAB: PRODUKTY (DODAWANIE I LISTA) ---
with tabs[1]:
    st.header("Lista produktów")
    df = get_products_df()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("Dodaj nowy produkt")
    kat_dict = get_categories()
    
    if kat_dict:
        with st.form("add_prod", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            name = c1.text_input("Nazwa produktu")
            qty = c2.number_input("Ilość", min_value=0)
            price = c3.number_input("Cena", min_value=0.0)
            cat_name = st.selectbox("Kategoria", options=list(kat_dict.keys()))
            
            if st.form_submit_button("Dodaj produkt"):
                if name:
                    supabase.table("produkty").insert({
                        "nazwa": name, "liczba": qty, "cena": price, "kategoria_id": kat_dict[cat_name]
                    }).execute()
                    st.success("Produkt dodany!")
                    st.rerun()
    else:
        st.error("Najpierw dodaj kategorię!")

# --- TAB: KATEGORIE ---
with tabs[2]:
    st.header("Kategorie")
    with st.form("add_cat"):
        new_cat = st.text_input("Nazwa nowej kategorii")
        if st.form_submit_button("Dodaj"):
            if new_cat:
                supabase.table("kategoria").insert({"nazwa": new_cat}).execute()
                st.rerun()

# --- TAB: ZARZĄDZANIE ---
with tabs[3]:
    st.header("Usuwanie i Eksport")
    df = get_products_df()
    if not df.empty:
        id_del = st.number_input("Podaj ID produktu do usunięcia", min_value=1, step=1)
        if st.button("USUŃ DEFINITYWNIE", type="primary"):
            supabase.table("produkty").delete().eq("id", id_del).execute()
            st.success("Usunięto!")
            st.rerun()
        
        st.divider()
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Pobierz bazę jako CSV", csv, "magazyn.csv", "text/csv")
