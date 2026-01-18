import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import plotly.express as px

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Magazynier Cloud PRO", layout="wide", page_icon="📦")

try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd połączenia! Sprawdź Secrets w Streamlit Cloud.")
    st.stop()

# --- 2. FUNKCJA LOGOWANIA (HISTORIA W BAZIE) ---
def zapisz_dziennik(akcja, szczegoly):
    try:
        supabase.table("dziennik").insert({
            "akcja": akcja, 
            "szczegoly": szczegoly,
            "uzytkownik": "Admin"
        }).execute()
    except Exception as e:
        st.error(f"Błąd zapisu w historii: {e}")

# --- 3. MENU ---
menu = st.sidebar.radio("Menu", [
    "📊 Dashboard", 
    "📦 Magazyn", 
    "💸 Sprzedaż", 
    "📂 Kategorie", 
    "📜 Historia", 
    "📈 Analiza", 
    "📝 Notatki"
])

# --- 4. MODUŁY ---

if menu == "📊 Dashboard":
    st.title("Statystyki Systemu")
    try:
        res_p = supabase.table("produkty").select("*").execute()
        res_s = supabase.table("sprzedaz").select("*").execute()
        df_p = pd.DataFrame(res_p.data)
        df_s = pd.DataFrame(res_s.data)

        c1, c2 = st.columns(2)
        if not df_p.empty:
            c1.metric("Produkty w bazie", len(df_p))
            total_money = df_s['suma'].sum() if not df_s.empty else 0
            c2.metric("Suma sprzedaży", f"{total_money:.2f} zł")
            st.dataframe(df_p, use_container_width=True)
        else:
            st.info("Baza jest pusta. Zacznij od dodania kategorii i produktów.")
    except Exception as e:
        st.error(f"Błąd Dashboardu: {e}")

elif menu == "📦 Magazyn":
    st.title("Zarządzanie Magazynem")
    try:
        res_k = supabase.table("kategoria").select("*").execute()
        df_k = pd.DataFrame(res_k.data)

        if df_k.empty:
            st.warning("Najpierw dodaj kategorię w zakładce 'Kategorie'!")
        else:
            with st.expander("Dodaj nowy produkt"):
                with st.form("add_product"):
                    nazwa = st.text_input("Nazwa produktu")
                    kat_id = st.selectbox("Kategoria", df_k['id'].tolist(), 
                                          format_func=lambda x: df_k[df_k['id']==x]['nazwa'].values[0])
                    c1, c2 = st.columns(2)
                    ilosc = c1.number_input("Ilość", min_value=1)
                    cena = c2.number_input("Cena (zł)", min_value=0.0)
                    if st.form_submit_button("Zapisz w chmurze"):
                        supabase.table("produkty").insert({
                            "nazwa": nazwa, "liczba": ilosc, "cena": cena, "kategoria_id": kat_id
                        }).execute()
                        zapisz_dziennik("DODANIE", f"Produkt: {nazwa}")
                        st.success("Dodano produkt!")
                        st.rerun()

        res_p = supabase.table("produkty").select("*").execute()
        if res_p.data:
            df_p = pd.DataFrame(res_p.data)
            st.subheader("Stan magazynowy")
            st.dataframe(df_p, use_container_width=True)
            
            st.divider()
            st.subheader("Usuwanie Produktu")
            with st.form("del_form"):
                to_del = st.selectbox("Wybierz produkt do usunięcia", df_p['id'].tolist(), 
                                      format_func=lambda x: df_p[df_p['id']==x]['nazwa'].values[0])
                if st.form_submit_button("Usuń trwale produkt"):
                    supabase.table("produkty").delete().eq("id", to_del).execute()
                    zapisz_dziennik("USUNIĘCIE", f"ID produktu: {to_del}")
                    st.success("Produkt usunięty!")
                    st.rerun()
    except Exception as e:
        st.error(f"Błąd: {e}")

elif menu == "💸 Sprzedaż":
    st.title("Panel Sprzedaży")
    try:
        res_p = supabase.table("produkty").select("*").gt("liczba", 0).execute()
        df_p = pd.DataFrame(res_p.data)
        if not df_p.empty:
            with st.form("sale_form"):
                pid = st.selectbox("Produkt", df_p['id'].tolist(), 
                                   format_func=lambda x: df_p[df_p['id']==x]['nazwa'].values[0])
                ile = st.number_input("Ilość sztuk", min_value=1)
                if st.form_submit_button("Finalizuj sprzedaż"):
                    row = df_p[df_p['id'] == pid].iloc[0]
                    if ile <= row['liczba']:
                        nova_ilosc = int(row['liczba'] - ile)
                        total = ile * float(row['cena'])
                        supabase.table("produkty").update({"liczba": nova_ilosc}).eq("id", pid).execute()
                        supabase.table("sprzedaz").insert({"produkt_id": pid, "ilosc": ile, "suma": total}).execute()
                        zapisz_dziennik("SPRZEDAŻ", f"{ile}x {row['nazwa']}")
                        st.success(f"Sprzedano! Łącznie: {total:.2f} zł")
                        st.rerun()
                    else:
                        st.error("Brak wystarczającej ilości towaru!")
    except Exception as e:
        st.error(f"Błąd: {e}")

elif menu == "📂 Kategorie":
    st.title("Zarządzanie Kategoriami")
    try:
        # Dodawanie kategorii
        with st.form("kat_form"):
            nazwa_k = st.text_input("Nowa kategoria")
            if st.form_submit_button("Dodaj"):
                if nazwa_k:
                    supabase.table("kategoria").insert({"nazwa": nazwa_k}).execute()
                    zapisz_dziennik("KATEGORIA", f"Dodano: {nazwa_k}")
                    st.success(f"Dodano kategorię: {nazwa_k}")
                    st.rerun()
        
        st.divider()
        
        # Wyświetlanie i usuwanie kategorii
        res_k = supabase.table("kategoria").select("*").execute()
        if res_k.data:
            df_k = pd.DataFrame(res_k.data)
            st.subheader("Lista kategorii")
            st.table(df_k)
            
            with st.expander("Usuń kategorię"):
                with st.form("del_kat_form"):
                    kat_to_del = st.selectbox("Wybierz kategorię do usunięcia", df_k['id'].tolist(),
                                             format_func=lambda x: df_k[df_k['id']==x]['nazwa'].values[0])
                    st.warning("Uwaga: Możesz usunąć tylko kategorię, która nie zawiera żadnych produktów.")
                    if st.form_submit_button("Usuń kategorię"):
                        try:
                            supabase.table("kategoria").delete().eq("id", kat_to_del).execute()
                            zapisz_dziennik("USUNIĘCIE KAT.", f"ID kategorii: {kat_to_del}")
                            st.success("Kategoria została usunięta!")
                            st.rerun()
                        except:
                            st.error("Nie można usunąć kategorii! Najpierw usuń wszystkie produkty przypisane do tej kategorii.")
    except Exception as e:
        st.error(f"Błąd: {e}")

elif menu == "📜 Historia":
    st.title("Dziennik Zdarzeń (Logi w bazie)")
    try:
        res = supabase.table("dziennik").select("*").order("id", desc=True).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data), use_container_width=True)
        else:
            st.info("Historia jest pusta.")
    except Exception as e:
        st.error(f"Nie można pobrać historii: {e}")

elif menu == "📈 Analiza":
    st.title("Analityka i Wykresy")
    try:
        res_s = supabase.table("sprzedaz").select("*").execute()
        res_p = supabase.table("produkty").select("id, nazwa").execute()
        df_s = pd.DataFrame(res_s.data)
        df_p = pd.DataFrame(res_p.data)

        if not df_s.empty and not df_p.empty:
            df_merged = df_s.merge(df_p, left_on="produkt_id", right_on="id")
            profit_data = df_merged.groupby("nazwa")["suma"].sum().reset_index()

            fig = px.pie(profit_data, values='suma', names='nazwa', title='Udział w zysku', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
            zapisz_dziennik("RAPORT", "Wygenerowano analizę sprzedaży")
        else:
            st.info("Brak danych do analizy.")
    except Exception as e:
        st.error(f"Błąd analizy: {e}")

elif menu == "📝 Notatki":
    st.title("Notatki Magazynowe (Nowa tabela)")
    with st.form("note_form"):
        tresc = st.text_area("Treść notatki")
        ważne = st.checkbox("Ważne")
        if st.form_submit_button("Zapisz w Supabase"):
            if tresc:
                supabase.table("notatki").insert({"tresc": tresc, "wazne": ważne}).execute()
                zapisz_dziennik("NOTATKA", f"Dodano notatkę: {tresc[:20]}...")
                st.success("Zapisano notatkę!")
                st.rerun()

    st.divider()
    res_n = supabase.table("notatki").select("*").order("id", desc=True).execute()
    if res_n.data:
        for n in res_n.data:
            ikona = "🚨" if n['wazne'] else "📌"
            # Dodanie opcji usuwania notatki
            col1, col2 = st.columns([0.9, 0.1])
            col1.write(f"{ikona} **{n['data'][:10]}**: {n['tresc']}")
            if col2.button("❌", key=n['id']):
                supabase.table("notatki").delete().eq("id", n['id']).execute()
                st.rerun()
