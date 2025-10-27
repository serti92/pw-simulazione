# Gestisce l'interfaccia utente con Streamlit e chiama la logica dal modulo 'app'.

import streamlit as st
import app
import copy

st.set_page_config(
    page_title="Simulatore Tenuta Pegaso",
    page_icon="🍇",
    layout="wide"
)

st.title("🍇 Simulatore di Vendemmia - Tenuta Pegaso")
st.markdown("Strumento di supporto decisionale per l'analisi di scenario e rischio.")


# Carica la configurazione usando la cache di Streamlit per efficienza
@st.cache_data
def cached_load_config():
    # Funzione per messa in cache risultato
    return app.carica_config()


try:
    CONFIG = cached_load_config()
    settings = CONFIG.get('global_settings', {})
    N_ITERAZIONI = settings.get('n_iterazioni_montecarlo', 1000)
    CARTELLA_OUTPUT = settings.get('cartella_output_csv', 'output_csv_default')
except Exception as e:
    st.error(f"Errore fatale nel caricamento di `config.json`: {e}")
    st.stop()

# --- Sidebar di Navigazione per il cambio di pagina ---
st.sidebar.header("Menu di Navigazione")
pagina_selezionata = st.sidebar.radio(
    "Seleziona una funzionalità",
    ("Confronto Scenari", "Simulatore What-If"),
    key="menu_principale"
)
st.sidebar.markdown("---")
st.sidebar.info(f"N° Iterazioni Monte Carlo: **{N_ITERAZIONI}**")

# --- Pagina 1: Confronto Scenari ---
if pagina_selezionata == "Confronto Scenari":
    st.header("Dashboard: Confronto Scenari Predefiniti")
    st.markdown(
        "Questa pagina esegue l'analisi Monte Carlo sui 3 scenari definiti nel `config.json` "
        "(Pessimistico, Reale, Ottimistico) e ne confronta i risultati."
    )
    st.divider()

    # Pulsante per avviare la simulazione
    if st.button(f"Avvia Simulazione Monte Carlo ({N_ITERAZIONI} iterazioni)", type="primary"):

        with st.spinner("Esecuzione simulazione in corso... (potrebbe richiedere alcuni secondi)"):
            try:
                # Chiama le funzioni dal modulo 'app' per fare il lavoro pesante
                df_risultati = app.run_montecarlo(CONFIG, N_ITERAZIONI)
                summary_df, summary_print = app.analizza_risultati(df_risultati)

                path_raw, path_summary = app.salva_risultati(df_risultati, summary_print, CARTELLA_OUTPUT)

                st.success("Simulazione completata!")

                # Mostra i risultati nell'interfaccia
                st.subheader("Risultati Aggregati (Statistiche)")
                st.dataframe(summary_print, use_container_width=True)

                if path_raw and path_summary:
                    st.subheader("File Generati")
                    st.info(f"Dati grezzi (RAW) salvati in: `{path_raw}`")
                    st.info(f"Dati di summary salvati in: `{path_summary}`")

            except Exception as e:
                st.error(f"Errore durante l'esecuzione della simulazione: {e}")
                st.stop()

# --- Pagina 2: Simulatore What-If ---
elif pagina_selezionata == "Simulatore What-If":
    st.header("Simulatore 'What-If'")
    st.markdown("Modifica i parametri di uno scenario base per lanciare una simulazione personalizzata.")
    st.divider()

    # --- 1. Seleziona scenario base ---
    nomi_scenari = list(CONFIG['scenari'].keys())
    scenario_base_nome = st.selectbox(
        "Seleziona lo scenario da cui partire:",
        nomi_scenari,
        index=nomi_scenari.index('Reale')  # Default su 'Reale'
    )

    # Questo blocco viene eseguito solo se lo scenario è cambiato o se è la prima esecuzione per caircare i dati di default del JSON
    if 'whatif_scenario_corrente' not in st.session_state or st.session_state.whatif_scenario_corrente != scenario_base_nome:
        st.session_state.whatif_scenario_corrente = scenario_base_nome

        # Estraiamo i parametri di default dal CONFIG originale
        scenario_default = CONFIG['scenari'][scenario_base_nome]
        gen_params_default = CONFIG['par_gen_lotti']['resa_ettaro']

        # Popoliamo st.session_state con i valori iniziali del nuovo scenario
        for prod in gen_params_default['superficie_ha']:
            st.session_state[f"whatif_sup_{prod}"] = float(gen_params_default['superficie_ha'][prod])
            st.session_state[f"whatif_resa_{prod}"] = float(gen_params_default['resa_q_ha_media'][prod])

        for prod_info in scenario_default['prodotti']:
            st.session_state[f"whatif_prezzo_{prod_info['nome']}"] = float(prod_info['prezzo_kg'])

        for seq_key in ['manuale', 'meccanica']:
            seq_params = scenario_default[seq_key]
            st.session_state[f"whatif_cap_{seq_key}"] = float(seq_params['cap_q_gg'])
            st.session_state[f"whatif_costo_{seq_key}"] = float(seq_params['costo_euro_gg'])
            st.session_state[f"whatif_scarto_{seq_key}"] = float(seq_params['scarto_perc'])

    # --- Widget UI leggono e scrivono st.session_state ---
    st.subheader("Parametri Personalizzati")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### Produzione (Lotti)")
        for prod in CONFIG['par_gen_lotti']['resa_ettaro']['superficie_ha']:
            st.number_input(
                f"Superficie (ha) - {prod}",
                min_value=0.0,
                step=0.5,
                key=f"whatif_sup_{prod}"  # La key punta a st.session_state
            )
            st.number_input(
                f"Resa (q/ha) - {prod}",
                min_value=0.0,
                step=1.0,
                key=f"whatif_resa_{prod}"  # La key punta a st.session_state
            )

    with col2:
        st.markdown("#### Economia (Prezzi)")
        for prod_info in CONFIG['scenari'][scenario_base_nome]['prodotti']:
            st.number_input(
                f"Prezzo (€/kg) - {prod_info['nome']}",
                min_value=0.0,
                step=0.05,
                format="%.2f",
                key=f"whatif_prezzo_{prod_info['nome']}"  # La key punta a st.session_state
            )

    with col3:
        st.markdown("#### Processo (Sequenze)")
        for seq_key in ['manuale', 'meccanica']:
            st.markdown(f"**{seq_key.capitalize()}**")
            st.number_input(
                f"Capacità (q/gg) - {seq_key}",
                min_value=1.0,
                step=5.0,
                key=f"whatif_cap_{seq_key}"  # La key punta a st.session_state
            )
            st.number_input(
                f"Costo (€/gg) - {seq_key}",
                min_value=0.0,
                step=10.0,
                key=f"whatif_costo_{seq_key}"  # La key punta a st.session_state
            )
            st.slider(
                f"Scarto (%) - {seq_key}",
                min_value=0.0, max_value=1.0,
                step=0.005, format="%.1f%%",
                key=f"whatif_scarto_{seq_key}"  # La key punta a st.session_state
            )

    st.divider()

    # --- Bottone di avvio What-If ---
    if st.button(f"Avvia Simulazione What-If ({N_ITERAZIONI} iterazioni)", type="primary"):
        # Prima di lanciare la simulazione, creiamo una nuova configurazione
        # usando i valori che l'utente ha modificato presenti in st.session_state.
        config_whatif_final = copy.deepcopy(CONFIG)

        # Estraiamo i puntatori ai dizionari che modificheremo
        gen_params_whatif = config_whatif_final['par_gen_lotti']['resa_ettaro']
        # Creiamo un nuovo scenario basato su quello di partenza
        scenario_whatif = copy.deepcopy(config_whatif_final['scenari'][scenario_base_nome])

        # Aggiorniamo la config con i valori da session_state
        for prod in gen_params_whatif['superficie_ha']:
            gen_params_whatif['superficie_ha'][prod] = st.session_state[f"whatif_sup_{prod}"]
            gen_params_whatif['resa_q_ha_media'][prod] = st.session_state[f"whatif_resa_{prod}"]

        for prod_info in scenario_whatif['prodotti']:
            prod_info['prezzo_kg'] = st.session_state[f"whatif_prezzo_{prod_info['nome']}"]

        for seq_key in ['manuale', 'meccanica']:
            seq_params = scenario_whatif[seq_key]
            seq_params['cap_q_gg'] = st.session_state[f"whatif_cap_{seq_key}"]
            seq_params['costo_euro_gg'] = st.session_state[f"whatif_costo_{seq_key}"]
            seq_params['scarto_perc'] = st.session_state[f"whatif_scarto_{seq_key}"]

        # Rinominiamo lo scenario per chiarezza nei risultati e lo sostituiamo nella config
        config_whatif_final['scenari'] = {f"What-If (da {scenario_base_nome})": scenario_whatif}

        with st.spinner("Esecuzione simulazione 'What-If'..."):
            try:
                # Riconvalida la config modificata prima di eseguirla
                app.simulazione.validate_config(config_whatif_final)

                # Per la simulazione What-If, vogliamo che i parametri siano fissi --> Variabilità montecarlo a 0
                var_params_whatif = {
                    "capacita_sigma_percent": 0.0,
                    "costo_sigma_percent": 0.0,
                    "scarto_sigma_percent": 0.0
                }

                config_whatif_final['var_params'] = var_params_whatif

                # Esegui simulazione con la config utente
                df_risultati_whatif = app.run_montecarlo(config_whatif_final, N_ITERAZIONI)
                summary_df_whatif, summary_print_whatif = app.analizza_risultati(df_risultati_whatif)

                st.success("Simulazione 'What-If' completata!")

                # Mostra risultati
                st.subheader("Risultati Simulazione Personalizzata")
                st.dataframe(summary_print_whatif, use_container_width=True)

            except ValueError as ve:
                st.error(f"Errore di Validazione: I parametri inseriti non sono validi. Dettagli: {ve}")
            except Exception as e:
                st.error(f"Errore durante l'esecuzione: {e}")
