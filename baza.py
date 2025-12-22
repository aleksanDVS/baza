import streamlit as st
from supabase import create_client, Client

# --- KONFIGURACJA POŁĄCZENIA ---
# Dane pobierane ze Streamlit Secrets (Ustawienia na stronie streamlit.io)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("📦 Zarządzanie Magazynem")

# Tworzymy zakładki dla lepszej przejrzystości
tab1, tab2 = st.tabs(["Dodaj Produkt", "Dodaj Kategorię"])

# --- ZAKŁADKA: DODAWANIE KATEGORII ---
with tab2:
    st.header("Nowa Kategoria")
    with st.form("form_kategoria", clear_on_submit=True):
        kat_nazwa = st.text_input("Nazwa kategorii")
        kat_opis = st.text_area("Opis")
        submit_kat = st.form_submit_button("Zapisz kategorię")

        if submit_kat:
            if kat_nazwa:
                data = {"nazwa": kat_nazwa, "opis": kat_opis}
                response = supabase.table("kategoria").insert(data).execute()
                st.success(f"Dodano kategorię: {kat_nazwa}")
            else:
                st.error("Nazwa kategorii jest wymagana!")

# --- ZAKŁADKA: DODAWANIE PRODUKTÓW ---
with tab1:
    st.header("Nowy Produkt")
    
    # Pobieramy aktualne kategorie z bazy, aby móc je wybrać w dropdownie
    kategorie_data = supabase.table("kategoria").select("id, nazwa").execute()
    kategorie_dict = {item['nazwa']: item['id'] for item in kategorie_data.data}
    
    if not kategorie_dict:
        st.warning("Najpierw dodaj przynajmniej jedną kategorię!")
    else:
        with st.form("form_produkt", clear_on_submit=True):
            prod_nazwa = st.text_input("Nazwa produktu")
            prod_liczba = st.number_input("Liczba (szt.)", min_value=0, step=1)
            prod_cena = st.number_input("Cena", min_value=0.0, format="%.2f")
            
            # Wybór kategorii po nazwie, ale zapisujemy ID
            wybrana_kat_nazwa = st.selectbox("Kategoria", options=list(kategorie_dict.keys()))
            
            submit_prod = st.form_submit_button("Dodaj produkt")

            if submit_prod:
                if prod_nazwa:
                    prod_data = {
                        "nazwa": prod_nazwa,
                        "liczba": prod_liczba,
                        "cena": prod_cena,
                        "kategoria_id": kategorie_dict[wybrana_kat_nazwa]
                    }
                    supabase.table("Produkty").insert(prod_data).execute()
                    st.success(f"Produkt '{prod_nazwa}' został dodany!")
                else:
                    st.error("Nazwa produktu jest wymagana!")

# --- PODGLĄD DANYCH (OPCJONALNIE) ---
st.divider()
if st.checkbox("Pokaż listę produktów"):
    produkty = supabase.table("Produkty").select("nazwa, liczba, cena, kategoria(nazwa)").execute()
    if produkty.data:
        st.table(produkty.data)
