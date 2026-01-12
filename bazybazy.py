import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. KONFIGURACJA API ---
SUPABASE_URL = "https://pfrgvpybklrmjnyttduo.supabase.co"
SUPABASE_KEY = "sb_publishable_TRb3wyGLDjmxQPXQ2AhtYw_uzmHiwnm"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation" # Informuje API, by zwracało wstawione dane
}

# --- 2. FUNKCJE KOMUNIKACJI ---

def supabase_get(table, select="*"):
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
    response = requests.get(url, headers=HEADERS)
    return response.json()

def supabase_insert(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    requests.post(url, headers=HEADERS, json=data)

def supabase_update(table, data, column_name, value):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{column_name}=eq.{value}"
    requests.patch(url, headers=HEADERS, json=data)

# --- 3. PRZYKŁAD ZASTOSOWANIA W TWOIM KODZIE ---

# DASHBOARD (Pobieranie danych)
if st.sidebar.radio("Menu", ["Dashboard", "..."]) == "Dashboard":
    # Pobieranie produktów z joinem do kategorii (składnia PostgREST)
    data = supabase_get("produkty", "*,kategoria(nazwa)")
    df_p = pd.DataFrame(data)
    
    if not df_p.empty:
        # Przetworzenie zagnieżdżonego słownika z kategorią
        df_p['kategoria_nazwa'] = df_p['kategoria'].apply(lambda x: x['nazwa'] if x else "Brak")
        st.dataframe(df_p)

# DODAWANIE PRODUKTU (Wstawianie danych)
# (wewnątrz formularza)
if st.button("Zapisz produkt"):
    nowy_produkt = {
        "nazwa": "Mleko",
        "liczba": 10,
        "cena": 3.50,
        "kategoria_id": 1
    }
    supabase_insert("produkty", nowy_produkt)
    st.success("Dodano!")

# SPRZEDAŻ (Aktualizacja danych)
# (podczas potwierdzenia sprzedaży)
if st.button("Sprzedaj"):
    # Zmniejszenie stanu magazynowego
    supabase_update("produkty", {"liczba": 5}, "id", 123)
