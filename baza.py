import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- KONFIGURACJA POŁĄCZENIA ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Magazyn Supabase", layout="wide")
st.title("📦 System Zarządzania Produktami")

# Tworzymy trzy zakładki
tab1, tab2, tab3 = st.tabs(["➕ Dodaj Produkt", "📂 Dodaj Kategorię", "🔍 Podgląd Bazy"])

# --- ZAKŁADKA 2: DODAWANIE KATEGORII ---
with tab2:
    st.header("Dodaj nową kategorię")
    with st.form("form_kategoria", clear_on_submit=True):
        kat_nazwa = st.text_input("Nazwa kategorii")
        kat_opis = st.text_area("Opis")
        submit_kat = st.form_submit_button("Zapisz kategorię")

        if submit_kat:
            if kat_nazwa:
                supabase.table("kategoria").insert({"nazwa": kat_nazwa, "opis": kat_opis}).execute()
                st.success(f"Dodano kategorię: {kat_nazwa}")
                st.rerun() # Odśwież aplikację, by nowa kategoria pojawiła się na liście produktów
            else:
                st.error("Nazwa kategorii jest wymagana!")

# --- ZAKŁADKA 1: DODAWANIE PRODUKTÓW ---
with tab1:
    st.header("Dodaj nowy produkt")
    
    # Pobranie kategorii do listy rozwijanej
    res_kat = supabase.table("kategoria").select("id, nazwa").execute()
    kategorie_dict = {item['nazwa']: item['id'] for item in res_kat.data}
    
    if not kategorie_dict:
        st.warning("Najpierw dodaj przynajmniej jedną kategorię w zakładce 'Dodaj Kategorię'.")
    else:
        with st.form("form_produkt", clear_on_submit=True):
            prod_nazwa = st.text_input("Nazwa produktu")
            prod_liczba = st.number_input("Liczba (szt.)", min_value=0, step=1)
            prod_cena = st.number_input("Cena (PLN)", min_value=0.0, format="%.2f")
            wybrana_kat = st.selectbox("Wybierz kategorię", options=list(kategorie_dict.keys()))
            
            submit_prod = st.form_submit_button("Dodaj produkt")

            if submit_prod:
                if prod_nazwa:
                    nowy_produkt = {
                        "nazwa": prod_nazwa,
                        "liczba": prod_liczba,
                        "cena": prod_cena,
                        "kategoria_id": kategorie_dict[wybrana_kat]
                    }
                    supabase.table("Produkty").insert(nowy_produkt).execute()
                    st.success(f"Produkt '{prod_nazwa}' dodany pomyślnie!")
                else:
                    st.error("Nazwa produktu jest wymagana!")

# --- ZAKŁADKA 3: PODGLĄD BAZY ---
with tab3:
    st.header("Podgląd aktualnych danych")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Tabela: Kategorie")
        kat_data = supabase.table("kategoria").select("*").execute()
        if kat_data.data:
            df_kat = pd.DataFrame(kat_data.data)
            # Zmiana nazw kolumn na ładniejsze dla użytkownika
            df_kat.columns = ['ID', 'Nazwa', 'Opis']
            st.dataframe(df_kat, use_container_width=True, hide_index=True)
        else:
            st.info("Brak kategorii w bazie.")

    with col2:
        st.subheader("Tabela: Produkty")
        # Pobieramy produkty i dołączamy nazwę kategorii przez relację
        prod_data = supabase.table("Produkty").select("id, nazwa, liczba, cena, kategoria(nazwa)").execute()
        
        if prod_data.data:
            # Przekształcenie danych do płaskiej tabeli (wyciągnięcie nazwy kategorii z zagnieżdżonego słownika)
            rows = []
            for p in prod_data.data:
                rows.append({
                    "ID": p['id'],
                    "Nazwa": p['nazwa'],
                    "Ilość": p['liczba'],
                    "Cena": f"{p['cena']:.2f} zł",
                    "Kategoria": p['kategoria']['nazwa'] if p['kategoria'] else "Brak"
                })
            
            df_prod = pd.DataFrame(rows)
            st.dataframe(df_prod, use_container_width=True, hide_index=True)
        else:
            st.info("Brak produktów w bazie.")

    if st.button("Odśwież dane 🔄"):
        st.rerun()
