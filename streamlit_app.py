# Gestisce l'interfaccia utente con Streamlit e chiama la logica dal modulo 'app'.

import streamlit as st
import app
import copy
from datetime import datetime
import json

st.set_page_config(
    page_title="Simulatore Tenuta Pegaso",
    page_icon="🍇",
    layout="wide"
)

st.title("🍇 Simulatore di Vendemmia - Tenuta Pegaso")
st.markdown('''Strumento di supporto decisionale per l'analisi di scenario e rischio.  
⬅️ Apri il menù per le altre funzionalità''')



# Carica la configurazione usando la cache di Streamlit per efficienza
@st.cache_data
def cached_load_config():
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
    ("Confronto Scenari", "Simulatore What-If", "Configurazione"),
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
                # Chiama le funzioni dal modulo 'app'
                df_risultati = app.run_montecarlo(CONFIG, N_ITERAZIONI)
                summary_df, summary_print = app.analizza_risultati(df_risultati)

                # Salva i risultati nello stato della sessione per non fare refresh al download
                st.session_state.confronto_df_raw = df_risultati
                st.session_state.confronto_df_summary = summary_print

                st.success("Simulazione completata!")
            except Exception as e:
                st.error(f"Errore durante l'esecuzione della simulazione: {e}")
                st.stop()  # Interrompe l'esecuzione in caso di errore

    # Mostra i risultati solo se esistono nello stato della sessione
    if 'confronto_df_summary' in st.session_state and st.session_state.confronto_df_summary is not None:
        st.subheader("Risultati Aggregati (Statistiche)")

        # Mostra i risultati nell'interfaccia
        st.dataframe(
            st.session_state.confronto_df_summary,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Profitto Medio (€)": st.column_config.NumberColumn(format="euro"),
                "Profitto Std Dev (€)": st.column_config.NumberColumn(format="euro"),
                "Profitto 5° Perc. (€)": st.column_config.NumberColumn(format="euro"),
                "Profitto 95° Perc. (€)": st.column_config.NumberColumn(format="euro"),
                "Costo Medio (€)": st.column_config.NumberColumn(format="euro"),
                "Giorni Medi (arr.)": st.column_config.NumberColumn(format="%.2f"),
                "Quantità netta media": st.column_config.NumberColumn(format="%.2f"),
            }
        )

        st.subheader("Download Risultati")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        col_dl1, col_dl2,_ = st.columns([0.2,0.2,0.6])
        with col_dl1:
            st.download_button(
                label="📥 Scarica Dati RAW",
                data=st.session_state.confronto_df_raw.to_csv(index=False, sep=';', decimal='.').encode('utf-8'),
                file_name=f"run_montecarlo_raw_{timestamp}.csv",
                mime="text/csv",
                width='content'
            )
        with col_dl2:
            st.download_button(
                label="📥 Scarica Riepilogo",
                data=st.session_state.confronto_df_summary.to_csv(index=False, sep=';', decimal='.').encode('utf-8'),
                file_name=f"run_summary_{timestamp}.csv",
                mime="text/csv",
                width='content'
            )

# --- Pagina 2: Simulatore What-If ---
elif pagina_selezionata == "Simulatore What-If":
    st.header("Simulatore 'What-If'")
    st.markdown("Modifica i parametri di uno scenario base per lanciare una simulazione personalizzata.")
    st.divider()

    nomi_scenari = list(CONFIG['scenari'].keys())
    scenario_base_nome = st.selectbox(
        "Seleziona lo scenario da cui partire:",
        nomi_scenari,
        index=nomi_scenari.index('Reale')
    )
    if 'whatif_scenario_corrente' not in st.session_state or st.session_state.whatif_scenario_corrente != scenario_base_nome:

        #Cancella i valori vecchi dei widget dallo stato della sessione per evitare che ci siano disallineamenti con JSON
        for key in list(st.session_state.keys()):
            if key.startswith("whatif_"):
                del st.session_state[key]

        st.session_state.whatif_scenario_corrente = scenario_base_nome
        scenario_default = CONFIG['scenari'][scenario_base_nome]
        gen_params_default = CONFIG['par_gen_lotti']['resa_ettaro']

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

    st.subheader("Parametri Personalizzati")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Produzione (Lotti)")
        for prod in CONFIG['par_gen_lotti']['resa_ettaro']['superficie_ha']:
            st.number_input(f"Superficie (ha) - {prod}", min_value=0.0, step=0.5, key=f"whatif_sup_{prod}")
            st.number_input(f"Resa (q/ha) - {prod}", min_value=0.0, step=1.0, key=f"whatif_resa_{prod}")
    with col2:
        st.markdown("#### Economia (Prezzi)")
        for prod_info in CONFIG['scenari'][scenario_base_nome]['prodotti']:
            st.number_input(f"Prezzo (€/kg) - {prod_info['nome']}", min_value=0.0, step=0.05, format="%.2f",
                            key=f"whatif_prezzo_{prod_info['nome']}")
    with col3:
        st.markdown("#### Processo (Sequenze)")
        for seq_key in ['manuale', 'meccanica']:
            st.markdown(f"**{seq_key.capitalize()}**")
            st.number_input(f"Capacità (q/gg) - {seq_key}", min_value=1.0, step=5.0, key=f"whatif_cap_{seq_key}")
            st.number_input(f"Costo (€/gg) - {seq_key}", min_value=0.0, step=10.0, key=f"whatif_costo_{seq_key}")
            st.slider(f"Scarto (%) - {seq_key}", min_value=0.0, max_value=1.0, step=0.005, format="%.1f%%",
                      key=f"whatif_scarto_{seq_key}")

    st.divider()

    if st.button(f"Avvia Simulazione What-If ({N_ITERAZIONI} iterazioni)", type="primary"):
        config_whatif_final = copy.deepcopy(CONFIG)
        gen_params_whatif = config_whatif_final['par_gen_lotti']['resa_ettaro']
        scenario_whatif = copy.deepcopy(config_whatif_final['scenari'][scenario_base_nome])
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
        config_whatif_final['scenari'] = {f"What-If (da {scenario_base_nome})": scenario_whatif}

        with st.spinner("Esecuzione simulazione 'What-If'..."):
            try:
                app.simulazione.validate_config(config_whatif_final)
                var_params_whatif = {"capacita_sigma_percent": 0.0, "costo_sigma_percent": 0.0,
                                     "scarto_sigma_percent": 0.0}
                config_whatif_final['var_params'] = var_params_whatif

                df_risultati_whatif = app.run_montecarlo(config_whatif_final, N_ITERAZIONI)
                summary_df_whatif, summary_print_whatif = app.analizza_risultati(df_risultati_whatif)

                st.success("Simulazione 'What-If' completata!")
                st.session_state.whatif_results = summary_print_whatif  # Salva in stato

            except ValueError as ve:
                st.error(f"Errore di Validazione: I parametri inseriti non sono validi. Dettagli: {ve}")
            except Exception as e:
                st.error(f"Errore durante l'esecuzione: {e}")

    # Mostra i risultati What-If solo se esistono nello stato
    if 'whatif_results' in st.session_state and st.session_state.whatif_results is not None:
        st.subheader("Risultati Simulazione Personalizzata")
        st.dataframe(
            st.session_state.whatif_results,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Profitto Medio (€)": st.column_config.NumberColumn(format="euro"),
                "Profitto Std Dev (€)": st.column_config.NumberColumn(format="euro"),
                "Profitto 5° Perc. (€)": st.column_config.NumberColumn(format="euro"),
                "Profitto 95° Perc. (€)": st.column_config.NumberColumn(format="euro"),
                "Costo Medio (€)": st.column_config.NumberColumn(format="euro"),
                "Giorni Medi (arr.)": st.column_config.NumberColumn(format="%.2f"),
                "Quantità netta media": st.column_config.NumberColumn(format="%.2f"),
            }
        )

# Pagina 3: Configurazione ---
elif pagina_selezionata == "Configurazione":

    #Mostra toast salvataggio JSON dopo riavvio
    if "show_save_confirmation" in st.session_state:
        if st.session_state.show_save_confirmation:
            st.toast("Configurazione salvata e validata!", icon="✅")
        # Pulisce il flag per non mostrare di nuovo notifica
        del st.session_state.show_save_confirmation

    st.header("⚙️ Editor Configurazione")
    st.markdown(
        "Modifica i parametri globali, i limiti e gli scenari attualmente caricati dal file `config.json`."
    )
    st.warning(
        "**Importante:** Dopo aver salvato, la cache della configurazione verrà pulita e "
        "l'app si ricaricherà per applicare le modifiche."
    )

    # --- LOGICA DI CARICAMENTO IN SESSION_STATE ---
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            # Stato prima delle modifiche
            config_da_modificare = json.load(f)
    except Exception as e:
        st.error(f"Impossibile leggere config.json: {e}")
        st.stop()

    if 'config_editor_state' not in st.session_state:
        st.session_state.config_editor_state = copy.deepcopy(config_da_modificare)

    config_in_editing = st.session_state.config_editor_state

    # --- UI con schede ---
    tab_global, tab_limiti, tab_lotti, tab_var, tab_scenari = st.tabs([
        "Impostazioni Globali",
        "Limiti Validazione",
        "Generazione Lotti",
        "Parametri Varianza",
        "Scenari"
    ])

    # --- Tab 1: Global Settings  ---
    with tab_global:
        st.subheader("Impostazioni Globali")
        settings = config_in_editing.get('global_settings', {})
        col1, col2 = st.columns(2)
        with col1:
            settings['random_seed'] = st.number_input(
                "Random Seed",
                value=int(settings.get('random_seed', 42)),
                disabled=True
            )
            settings['n_iterazioni_montecarlo'] = st.number_input(
                "N° Iterazioni Monte Carlo",
                value=int(settings.get('n_iterazioni_montecarlo', 1000)),
                disabled=False
            )
        with col2:
            settings['kg_per_q'] = st.number_input(
                "kg per quintale",
                value=int(settings.get('kg_per_q', 100)),
                disabled=False
            )
            settings['cartella_output_csv'] = st.text_input(
                "Cartella Output CSV",
                value=settings.get('cartella_output_csv', 'N/D'),
                disabled=False
            )

    # --- Tab 2: Limiti Validazione  ---
    with tab_limiti:
        st.subheader("Limiti di Validazione")
        limiti = config_in_editing.get('validaz_limiti', {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("##### Scarto")
            limiti['scarto_min'] = st.number_input(
                "Scarto Min (%)",
                value=float(limiti.get('scarto_min', 0.0)),
                format="%.2f",
                disabled=False,
                key="lim_scarto_min",
                min_value=0.0,
                max_value=1.0
            )
            limiti['scarto_max'] = st.number_input(
                "Scarto Max (%)",
                value=float(limiti.get('scarto_max', 0.0)),
                format="%.2f",
                disabled=False,
                key="lim_scarto_max",
                min_value=0.0,
                max_value=1.0
            )
        with col2:
            st.markdown("##### Capacità")
            limiti['capacita_min_q_g'] = st.number_input(
                "Capacità Min (q/g)",
                value=int(limiti.get('capacita_min_q_g', 0)),
                disabled=False,
                key="lim_cap_min"
            )
            limiti['capacita_max_q_g'] = st.number_input(
                "Capacità Max (q/g)",
                value=int(limiti.get('capacita_max_q_g', 0)),
                disabled=False,
                key="lim_cap_max"
            )
        with col3:
            st.markdown("##### Costo")
            limiti['costo_min_euro_g'] = st.number_input(
                "Costo Min (€/g)",
                value=int(limiti.get('costo_min_euro_g', 0)),
                format="%d",
                disabled=False,
                key="lim_costo_min"
            )
            limiti['costo_max_euro_g'] = st.number_input(
                "Costo Max (€/g)",
                value=int(limiti.get('costo_max_euro_g', 0)),
                format="%d",
                disabled=False,
                key="lim_costo_max"
            )

    # --- Tab 3: Generazione Lotti  ---
    with tab_lotti:
        st.subheader("Parametri Generazione Lotti")
        lotti_params = config_in_editing.get('par_gen_lotti', {})
        st.text_input(
            "Modalità",
            value=lotti_params.get('modalita', 'N/D'),
            disabled=True,
            key="lotti_modalita"
        )

        resa_params = lotti_params.get('resa_ettaro', {})
        resa_params['resa_sigma_percent'] = st.number_input(
            "Sigma Resa (%)",
            value=float(resa_params.get('resa_sigma_percent', 0.0)),
            format="%.2f",
            disabled=False,
            key="lotti_sigma",
            min_value=0.0,
            max_value=1.0
        )

        st.divider()
        st.markdown("##### Parametri per Prodotto")
        superfici = resa_params.get('superficie_ha', {})
        rese = resa_params.get('resa_q_ha_media', {})
        prodotti = list(superfici.keys())

        if prodotti:
            cols = st.columns(len(prodotti))
            for i, prod in enumerate(prodotti):
                with cols[i]:
                    st.markdown(f"**{prod}**")
                    superfici[prod] = st.number_input(
                        f"Superficie (ha)",
                        value=float(superfici.get(prod, 0)),
                        disabled=False,
                        key=f"lotti_sup_{prod}"
                    )
                    rese[prod] = st.number_input(
                        f"Resa (q/ha) Media",
                        value=float(rese.get(prod, 0)),
                        disabled=False,
                        key=f"lotti_resa_{prod}"
                    )
        else:
            st.warning("Nessun prodotto definito in 'par_gen_lotti.resa_ettaro'.")

# --- Tab 4: Parametri Varianza  ---
    with tab_var:
        st.subheader("Parametri Varianza (Monte Carlo)")
        var_params = config_in_editing.get('var_params', {})
        col1, col2, col3 = st.columns(3)
        with col1:
            var_params['capacita_sigma_percent'] = st.number_input(
                "Sigma Capacità (%)",
                value=float(var_params.get('capacita_sigma_percent', 0.0)),
                format="%.2f",
                disabled=False,
                min_value=0.0,
                max_value=1.0,
                key="var_cap_sigma"
            )
        with col2:
            var_params['costo_sigma_percent'] = st.number_input(
                "Sigma Costo (%)",
                value=float(var_params.get('costo_sigma_percent', 0.0)),
                format="%.2f",
                disabled=False,
                min_value=0.0,
                max_value=1.0,
                key="var_costo_sigma"
            )
        with col3:
            var_params['scarto_sigma_percent'] = st.number_input(
                "Sigma Scarto (%)",
                value=float(var_params.get('scarto_sigma_percent', 0.0)),
                format="%.2f",
                disabled=False,
                min_value=0.0,
                max_value=1.0,
                key="var_scarto_sigma"
            )

    # --- Tab 5: Scenari  ---
    with tab_scenari:
        st.subheader("Definizione Scenari")
        scenari = config_in_editing.get('scenari', {})
        nomi_scenari = list(scenari.keys())

        if not nomi_scenari:
            st.warning("Nessun scenario definito.")
        else:
            scenario_tabs = st.tabs(nomi_scenari)
            for i, nome_scenario in enumerate(nomi_scenari):
                with scenario_tabs[i]:
                    scenario = scenari[nome_scenario]
                    st.markdown("##### Prezzi Prodotti")
                    prodotti_scenario = scenario.get('prodotti', [])

                    if prodotti_scenario:
                        cols_prod = st.columns(len(prodotti_scenario))
                        # 'enumerate' per accedere a prod_info per indice
                        for j, prod_info in enumerate(prodotti_scenario):
                            with cols_prod[j]:
                                nome_prod = prod_info.get('nome', 'N/D')
                                # Modifichiamo direttamente l'elemento nella lista
                                prodotti_scenario[j]['prezzo_kg'] = st.number_input(
                                    f"Prezzo (€/kg) - {nome_prod}",
                                    value=float(prod_info.get('prezzo_kg', 0)),
                                    format="%.2f",
                                    disabled=False,
                                    key=f"vis_{nome_scenario}_prezzo_{nome_prod}"
                                )
                    st.divider()
                    st.markdown("##### Parametri Processo")
                    col_man, col_mec = st.columns(2)

                    with col_man:
                        st.markdown("**Manuale**")
                        man = scenario.get('manuale', {})
                        man['cap_q_gg'] = st.number_input(
                            f"Capacità (q/gg)",
                            value=float(man.get('cap_q_gg', 0)),
                            disabled=False,
                            key=f"vis_{nome_scenario}_man_cap"
                        )
                        man['costo_euro_gg'] = st.number_input(
                            f"Costo (€/gg)",
                            value=float(man.get('costo_euro_gg', 0)),
                            format="%.0f",
                            disabled=False,
                            key=f"vis_{nome_scenario}_man_costo"
                        )
                        man['scarto_perc'] = st.number_input(
                            f"Scarto (%)",
                            value=float(man.get('scarto_perc', 0)),
                            format="%.2f",
                            disabled=False,
                            key=f"vis_{nome_scenario}_man_scarto",
                            min_value=0.0,
                            max_value=1.0
                        )
                with col_mec:
                    st.markdown("**Meccanica**")
                    mec = scenario.get('meccanica', {})
                    mec['cap_q_gg'] = st.number_input(
                        f"Capacità (q/gg)",
                        value=float(mec.get('cap_q_gg', 0)),
                        disabled=False,
                        key=f"vis_{nome_scenario}_mec_cap"
                    )
                    mec['costo_euro_gg'] = st.number_input(
                        f"Costo (€/gg)",
                        value=float(mec.get('costo_euro_gg', 0)),
                        format="%.0f",
                        disabled=False,
                        key=f"vis_{nome_scenario}_mec_costo"
                    )
                    mec['scarto_perc'] = st.number_input(
                        f"Scarto (%)",
                        value=float(mec.get('scarto_perc', 0)),
                        format="%.2f",
                        disabled=False,
                        key=f"vis_{nome_scenario}_mec_scarto",
                        min_value=0.0,
                        max_value=1.0
                    )

    st.divider()

    # --- LOGICA DI SALVATAGGIO ---
    if st.button("Salva Modifiche su `config.json`", type="primary"):

        # Get dizionario modificato "dopo" da session_state
        edited_config = st.session_state.config_editor_state

        # Confronta lo stato post modifiche (edited_config) con lo stato pre modifiche (config_da_modificare)
        if edited_config == config_da_modificare:
            st.warning("Nessuna modifica rilevata. Salvataggio non necessario.")
        else:
            #  Procede con salvataggio e validazione se presenti modifiche
            try:
                config_validata = copy.deepcopy(edited_config)
                if 'global_settings' in config_validata and 'kg_per_q' in config_validata['global_settings']:
                    config_validata['kg_per_q'] = config_validata['global_settings']['kg_per_q']

                app.simulazione.validate_config(config_validata)

                #Salvataggio su disco
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(edited_config, f, indent=2, ensure_ascii=False)

                #Pulizia cache e ricarica
                st.cache_data.clear()
                del st.session_state.config_editor_state

                if 'confronto_df_summary' in st.session_state:
                    del st.session_state.confronto_df_summary
                if 'confronto_df_raw' in st.session_state:
                    del st.session_state.confronto_df_raw
                if 'whatif_results' in st.session_state:
                    del st.session_state.whatif_results

                st.session_state.show_save_confirmation = True
                st.rerun()

            except ValueError as ve:
                st.error(f"Errore di Validazione Logica: {ve}. Salvataggio annullato.")
            except Exception as e:
                st.error(f"Errore during saving the file: {e}. Salvataggio annullato.")