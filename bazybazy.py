import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from st_supabase_connection import SupabaseConnection

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Sklep Magazynier Pro", layout="wide", page_icon="🧾")

# Połączenie z Supabase
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. FUNKCJE POMOCNICZE ---

def zapisz_w_dzienniku(akcja, szczegoly, uzytkownik="Admin"):
    data = {
        "data": datetime.now().isoformat(),
        "akcja": akcja,
        "szczegoly": szczegoly,
        "uzytkownik": uzytkownik
    }
    conn.table("dziennik").insert(data).execute()

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
SUMA:       {suma:.2f} zł
====================================
Dziękujemy za zakupy!
"""

# --- 3. NAWIGACJA ---
st.sidebar.title("🏢 Menu Główne")
menu = st.sidebar.radio("Wybierz moduł:", ["📊 Dashboard", "📦 Magazyn", "💸 Sprzedaż", "📂 Kategorie", "⚙️ Zarządzanie", "📜 Historia Operacji"])

# --- 4. MODUŁY APLIKACJI ---

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("Statystyki i Bilans")
    
    # Pobieranie danych z Supabase (JOIN przez .select)
    res_p = conn.table("produkty").select("*, kategoria(nazwa)").execute()
    res_s = conn.table("sprzedaz").select("*, produkty(nazwa)").execute()
    
    df_p = pd.DataFrame(res_p.data)
    df_s = pd.DataFrame(res_s.data)

    if not df_p.empty:
        # Mapowanie nazwy kategorii z relacji
        df_p['kategoria_nazwa'] = df_p['kategoria'].apply(lambda x: x['nazwa'] if x else "Brak")
        
        # Obliczenia sprzedaży
        total_income = df_s['suma'].sum() if not df_s.empty else 0
        current_stock = df_p['liczba'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Całkowity Przychód", f"{total_income:,.2f} zł")
        c2.metric("W magazynie (szt.)", int(current_stock))
        
        if not df_s.empty:
            df_s['produkt_nazwa'] = df_s['produkty'].apply(lambda x: x['nazwa'] if x else "Nieznany")
            sprzedane_suma = df_s.groupby('produkt_nazwa')['ilosc'].sum().reset_index()
            c3.metric("Sprzedano (szt.)", int(sprzedane_suma['ilosc'].sum()))
            
            st.divider()
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.plotly_chart(px.pie(df_p, values='liczba', names='kategoria_nazwa', title="Zapas wg kategorii", hole=0.4), use_container_width=True)
            with col_g2:
                st.plotly_chart(px.bar(sprzedane_suma, x='produkt_nazwa', y='ilosc', title="Ilość sprzedanych produktów"), use_container_width=True)
    else:
        st.info("Baza danych produktów jest pusta.")

# --- MAGAZYN ---
elif menu == "📦 Magazyn":
    st.title("Zarządzanie Towarem")
    res_kat = conn.table("kategoria").select("*").execute()
    df_kat = pd.DataFrame(res_kat.data)

    with st.expander("➕ Dodaj nowy produkt"):
        if not df_kat.empty:
            with st.form("add_p", clear_on_submit=True):
                n = st.text_input("Nazwa produktu")
                k_name = st.selectbox("Kategoria", df_kat['nazwa'].tolist())
                c1, c2 = st.columns(2)
                l = c1.number_input("Ilość", min_value=1)
                p = c2.number_input("Cena", min_value=0.0)
                
                if st.form_submit_button("Zapisz"):
                    k_id = df_kat[df_kat['nazwa'] == k_name]['id'].values[0]
                    new_prod = {"nazwa": n, "liczba": l, "cena": p, "kategoria_id": int(k_id)}
                    conn.table("produkty").insert(new_prod).execute()
                    zapisz_w_dzienniku("DODANIE", f"Dodano produkt: {n}")
                    st.rerun()
        else:
            st.warning("Najpierw dodaj kategorię!")

    # Wyświetlanie tabeli
    res_v = conn.table("produkty").select("id, nazwa, liczba, cena, kategoria(nazwa)").execute()
    if res_v.data:
        df_v = pd.DataFrame(res_v.data)
        df_v['kategoria'] = df_v['kategoria'].apply(lambda x: x['nazwa'] if x else "Brak")
        st.dataframe(df_v, use_container_width=True, hide_index=True)

# --- SPRZEDAŻ ---
elif menu == "💸 Sprzedaż":
    st.title("Punkt Sprzedaży")
    res_stock = conn.table("produkty").select("*").gt("liczba", 0).execute()
    df_stock = pd.DataFrame(res_stock.data)
    
    if not df_stock.empty:
        with st.form("sale_form"):
            prod_name = st.selectbox("Wybierz produkt", df_stock['nazwa'].tolist())
            ile = st.number_input("Ilość", min_value=1, step=1)
            confirm = st.form_submit_button("Potwierdź Sprzedaż")
            
            if confirm:
                row = df_stock[df_stock['nazwa'] == prod_name].iloc[0]
                if ile <= row['liczba']:
                    nowa_liczba = int(row['liczba'] - ile)
                    suma = ile * float(row['cena'])
                    
                    # Update magazynu
                    conn.table("produkty").update({"liczba": nowa_liczba}).eq("id", row['id']).execute()
                    
                    # Insert sprzedaży
                    sprzedaz_data = {
                        "data": datetime.now().isoformat(),
                        "produkt_id": int(row['id']),
                        "ilosc": ile,
                        "suma": suma
                    }
                    conn.table("sprzedaz").insert(sprzedaz_data).execute()
                    
                    zapisz_w_dzienniku("SPRZEDAŻ", f"Sprzedano {ile}x {prod_name}")
                    st.session_state.paragon_data = generuj_paragon(prod_name, ile, row['cena'], suma)
                    st.session_state.sukces = True
                    st.success(f"Sprzedano! Wartość: {suma:.2f} zł")
                else:
                    st.error(f"Niewystarczająca ilość (Dostępne: {row['liczba']})")

        if st.session_state.get('sukces'):
            st.download_button("📥 Pobierz Potwierdzenie (TXT)", st.session_state.paragon_data, f"paragon_{datetime.now().strftime('%H%M%S')}.txt")
    else:
        st.warning("Brak towaru w magazynie.")

# --- KATEGORIE ---
elif menu == "📂 Kategorie":
    st.title("Kategorie")
    with st.form("add_k"):
        nk = st.text_input("Nazwa nowej kategorii")
        if st.form_submit_button("Dodaj"):
            conn.table("kategoria").insert({"nazwa": nk}).execute()
            zapisz_w_dzienniku("KATEGORIA", f"Dodano kategorię: {nk}")
            st.rerun()
    
    res_k = conn.table("kategoria").select("*").execute()
    st.table(pd.DataFrame(res_k.data))

# --- ZARZĄDZANIE ---
elif menu == "⚙️ Zarządzanie":
    st.title("Usuwanie danych")
    col_u1, col_u2 = st.columns(2)
    
    with col_u1:
        res_p = conn.table("produkty").select("id, nazwa").execute()
        df_p = pd.DataFrame(res_p.data)
        if not df_p.empty:
            p_del = st.selectbox("Wybierz produkt do usunięcia", df_p['nazwa'].tolist())
            if st.button("Usuń Produkt"):
                conn.table("produkty").delete().eq("nazwa", p_del).execute()
                zapisz_w_dzienniku("USUNIĘCIE", f"Usunięto produkt: {p_del}")
                st.rerun()

    with col_u2:
        res_k = conn.table("kategoria").select("id, nazwa").execute()
        df_k = pd.DataFrame(res_k.data)
        if not df_k.empty:
            k_del = st.selectbox("Wybierz kategorię do usunięcia", df_k['nazwa'].tolist())
            if st.button("Usuń Kategorię"):
                conn.table("kategoria").delete().eq("nazwa", k_del).execute()
                zapisz_w_dzienniku("USUNIĘCIE", f"Usunięto kategorię: {k_del}")
                st.rerun()

# --- HISTORIA ---
elif menu == "📜 Historia Operacji":
    st.title("📜 Dziennik zdarzeń")
    res_log = conn.table("dziennik").select("*").order("id", desc=True).execute()
    if res_log.data:
        st.dataframe(pd.DataFrame(res_log.data), use_container_width=True, hide_index=True)
