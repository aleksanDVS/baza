import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Magazynier Pro Cloud", layout="wide", page_icon="🧾")

# Establish connection using Streamlit Secrets
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd połączenia! Sprawdź Secrets w Streamlit Cloud.")
    st.stop()

# --- 2. HELPER FUNCTIONS ---
def zapisz_dziennik(akcja, szczegoly):
    try:
        # Matches schema: data, akcja, szczegoly, uzytkownik
        supabase.table("dziennik").insert({
            "data": datetime.now().isoformat(),
            "akcja": akcja, 
            "szczegoly": szczegoly,
            "uzytkownik": "System"
        }).execute()
    except:
        pass 

# --- 3. NAVIGATION ---
menu = st.sidebar.radio("Nawigacja", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "📜 Historia"])

# --- 4. MODULES ---

if menu == "📊 Dashboard":
    st.title("Statystyki i Bilans")
    res_p = supabase.table("produkty").select("*").execute()
    res_s = supabase.table("sprzedaz").select("*").execute()
    df_p = pd.DataFrame(res_p.data)
    df_s = pd.DataFrame(res_s.data)

    if not df_p.empty:
        c1, c2 = st.columns(2)
        c1.metric("Suma produktów", len(df_p))
        income = df_s['suma'].sum() if not df_s.empty else 0
        c2.metric("Suma sprzedaży", f"{income:.2f} zł")
    else:
        st.info("Baza danych jest pusta.")

elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    res_kat = supabase.table("kategoria").select("*").execute()
    df_kat = pd.DataFrame(res_kat.data)

    if not df_kat.empty:
        with st.expander("➕ Dodaj nowy produkt"):
            with st.form("add_product", clear_on_submit=True):
                nazwa = st.text_input("Nazwa produktu")
                kat_id = st.selectbox("Kategoria", df_kat['id'].tolist(), 
                                      format_func=lambda x: df_kat[df_kat['id']==x]['nazwa'].values[0])
                c1, c2 = st.columns(2)
                ilosc = c1.number_input("Ilość", min_value=1)
                cena = c2.number_input("Cena", min_value=0.0)
                
                if st.form_submit_button("Zapisz"):
                    supabase.table("produkty").insert({
                        "nazwa": nazwa, "liczba": ilosc, "cena": cena, "kategoria_id": kat_id
                    }).execute()
                    zapisz_dziennik("DODANIE", f"Dodano: {nazwa}")
                    st.success("Zapisano!")
                    st.rerun()

    res_p = supabase.table("produkty").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        st.subheader("Aktualny Stan")
        st.dataframe(df_p, use_container_width=True)

        st.divider()
        st.subheader("🗑️ Usuń produkt")
        with st.form("delete_product"):
            # FIX: Properly closed string literals and brackets below
            to_delete = st.selectbox(
                "Wybierz produkt do usunięcia", 
                df_p['id'].tolist(), 
                format_func=lambda x: df_p[df_p['id'] == x]['nazwa'].values[0]
            )
            if st.form_submit_button("Usuń trwale"):
                supabase.table("produkty").delete().eq("id", to_delete).execute()
                zapisz_dziennik("USUNIĘCIE", f"Usunięto ID: {to_delete}")
                st.success("Usunięto!")
                st.rerun()

elif menu == "💸 Sprzedaż":
    st.title("Punkt Sprzedaży")
    res_p = supabase.table("produkty").select("*").gt("liczba", 0).execute()
    df_p = pd.DataFrame(res_p.data)

    if not df_p.empty:
        with st.form("sale"):
            p_id = st.selectbox("Produkt", df_p['id'].tolist(), 
                                format_func=lambda x: df_p[df_p['id']==x]['nazwa'].values[0])
            ile = st.number_input("Ilość", min_value=1)
            
            if st.form_submit_button("Potwierdź Sprzedaż"):
                row = df_p[df_p['id'] == p_id].iloc[0]
                if ile <= row['liczba']:
                    nowa_liczba = int(row['liczba'] - ile)
                    suma = ile * float(row['cena'])
                    # Update stock and record sale
                    supabase.table("produkty").update({"liczba": nowa_liczba}).eq("id", p_id).execute()
                    supabase.table("sprzedaz").insert({"produkt_id": p_id, "ilosc": ile, "suma": suma}).execute()
                    zapisz_dziennik("SPRZEDAŻ", f"Sprzedano {ile}x {row['nazwa']}")
                    st.success("Sprzedano!")
                    st.rerun()
                else:
                    st.error("Niewystarczająca ilość towaru!")

elif menu == "📂 Kategorie":
    st.title("Kategorie")
    with st.form("add_kat"):
        nowa_kat = st.text_input("Nowa kategoria")
        if st.form_submit_button("Dodaj"):
            supabase.table("kategoria").insert({"nazwa": nowa_kat}).execute()
            st.rerun()
    res = supabase.table("kategoria").select("*").execute()
    if res.data:
        st.table(pd.DataFrame(res.data)[['nazwa']])

elif menu == "📜 Historia":
    st.title("Historia")
    res_h = supabase.table("dziennik").select("*").order("id", desc=True).execute()
    if res_h.data:
        st.dataframe(pd.DataFrame(res_h.data), use_container_width=True)
