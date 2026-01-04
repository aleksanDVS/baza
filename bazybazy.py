# --- MODUŁ 1: DASHBOARD (Z LEGENDĄ PRODUKTÓW) ---
if menu == "📊 Dashboard":
    st.title("Statystyki i Bilans")

    df_p = pd.read_sql_query("SELECT id, nazwa, liczba, cena FROM produkty", conn)
    df_s = pd.read_sql_query("SELECT produkt_id, ilosc FROM sprzedaz", conn)

    if not df_p.empty:
        # Obliczenia bilansu
        sprzedane_suma = df_s.groupby('produkt_id')['ilosc'].sum().reset_index()
        sprzedane_suma.columns = ['id', 'Sprzedano']
        bilans = pd.merge(df_p, sprzedane_suma, on='id', how='left').fillna(0)
        bilans['Sprzedano'] = bilans['Sprzedano'].astype(int)
        bilans['Łącznie było'] = bilans['liczba'] + bilans['Sprzedano']

        # GŁÓWNE METRYKI (to co już masz)
        total_income = pd.read_sql_query("SELECT SUM(suma) FROM sprzedaz", conn).iloc[0,0] or 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Całkowity Przychód", f"{total_income:,.2f} zł")
        c2.metric("Produkty w magazynie", int(bilans['liczba'].sum()))
        c3.metric("Suma sprzedanych sztuk", int(bilans['Sprzedano'].sum()))

        st.divider()

        # --- TWOJA NOWA LEGENDA (Wyszczególnienie produktów) ---
        st.subheader("📝 Legenda sprzedaży (szczegóły produktów)")
        
        # Tworzymy kolumny dla legendy, żeby nie zajmowała za dużo miejsca w pionie
        col_leg1, col_leg2 = st.columns(2)
        
        # Sortujemy od najlepiej sprzedających się
        bilans_sorted = bilans.sort_values(by='Sprzedano', ascending=False)
        
        for i, row in bilans_sorted.iterrows():
            # Decydujemy, w której kolumnie wyświetlić produkt
            target_col = col_leg1 if i % 2 == 0 else col_leg2
            
            # Wyświetlamy informację o produkcie
            target_col.write(f"🔹 **{row['nazwa']}**: sprzedano **{row['Sprzedano']}** szt. (zostało: {row['liczba']})")

        st.divider()
        
        # --- TABELA BILANSU (opcjonalnie, jeśli chcesz ją zostawić pod spodem) ---
        st.subheader("📋 Pełna tabela bilansowa")
        st.dataframe(bilans[['nazwa', 'Łącznie było', 'Sprzedano', 'liczba']], 
                     column_config={"nazwa": "Produkt", "liczba": "Zostało"},
                     use_container_width=True, hide_index=True)
