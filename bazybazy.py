# --- MODUŁ 3: SPRZEDAŻ (POPRAWIONY) ---
elif menu == "💸 Sprzedaż":
    st.title("Punkt Sprzedaży")
    df_stock = pd.read_sql_query("SELECT id, nazwa, liczba, cena FROM produkty WHERE liczba > 0", conn)
    
    if not df_stock.empty:
        # Tworzymy formularz
        with st.form("sale_form"):
            prod = st.selectbox("Wybierz produkt", df_stock['nazwa'].tolist())
            ile = st.number_input("Ilość", min_value=1, step=1)
            confirm = st.form_submit_button("Potwierdź Sprzedaż")
            
            if confirm:
                row = df_stock[df_stock['nazwa'] == prod].iloc[0]
                if ile <= row['liczba']:
                    suma = ile * row['cena']
                    cur = conn.cursor()
                    cur.execute("UPDATE produkty SET liczba = liczba - ? WHERE id = ?", (ile, int(row['id'])))
                    cur.execute("INSERT INTO sprzedaz (data, produkt_id, ilosc, suma) VALUES (?,?,?,?)", 
                                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(row['id']), ile, suma))
                    conn.commit()
                    zapisz_w_dzienniku("SPRZEDAŻ", f"Sprzedano {ile}x {prod} za {suma:.2f} zł")
                    
                    # Zapisujemy dane paragonu w pamięci sesji, aby pokazać go POZA formularzem
                    st.session_state.ostatni_paragon = generuj_paragon(prod, ile, row['cena'], suma)
                    st.session_state.sprzedano_sukces = True
                    st.success(f"Sprzedano! Wartość: {suma:.2f} zł")
                else:
                    st.error("Brak wystarczającej ilości towaru!")

        # WYŚWIETLAMY PRZYCISK POBIERANIA POZA FORMULARZEM
        if "sprzedano_sukces" in st.session_state and st.session_state.sprzedano_sukces:
            st.download_button(
                label="📥 Pobierz Potwierdzenie (TXT)", 
                data=st.session_state.ostatni_paragon, 
                file_name=f"paragon_{datetime.now().strftime('%H%M%S')}.txt"
            )
            # Opcjonalnie: czyścimy stan po pokazaniu przycisku, żeby nie wisiał tam wiecznie
            # st.session_state.sprzedano_sukces = False 
    else:
        st.warning("Brak towaru.")
