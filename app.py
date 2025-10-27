import json
import simulazione
import pandas as pd
import numpy as np
import copy
import os
from datetime import datetime

def carica_config(config_path='config.json') -> dict:
    """Carica e valida la configurazione JSON."""
    print(f"Caricamento di {config_path}...")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"ERRORE: Impossibile caricare {config_path}. Dettagli: {e}")
        raise

    # Cerca kg_per_q in global_settings e al primo livello.
    if 'global_settings' in config and 'kg_per_q' in config['global_settings']:
        config['kg_per_q'] = config['global_settings']['kg_per_q']

    # Valida la configurazione prima di procedere
    try:
        simulazione.validate_config(config)
        print("Configurazione validata con successo.")
        return config
    except ValueError as e:
        print(f"ERRORE: Configurazione non valida. Dettagli: {e}")
        raise


def run_montecarlo(config: dict, n_iter: int) -> pd.DataFrame:
    """
    Esegue la simulazione Monte Carlo per tutti gli scenari e sequenze.
    """
    print(f"\n--- AVVIO SIMULAZIONE MONTE CARLO ({n_iter} iterazioni) ---")

    # Lista per conservare tutti i risultati
    risultati = []

    # Estraiamo i parametri globali che ci servono
    var_params = config['var_params']
    global_params = config

    # Imposta il seed una sola volta all'inizio
    simulazione.set_seed(config)

    for i in range(n_iter):
        if (i + 1) % 200 == 0:
            print(f"Completata iterazione {i + 1} di {n_iter}...")

        lotti_generati = simulazione.gen_random_lotti(config)

        # Itera su ogni scenario (Pessimistico, Reale, Ottimistico)
        for nome_scenario, config_scenario in config['scenari'].items():

            # Itera sulle sequenze
            for seq_chiave in ['manuale', 'meccanica']:
                # Esegui la simulazione singola
                kpi = simulazione.run_single_simulation(
                    generated_lots=lotti_generati,
                    config_scenario=config_scenario,
                    seq_chiave=seq_chiave,
                    var_params=var_params,
                    global_params=global_params
                )

                # Salva i risultati
                risultati.append({
                    'iterazione': i,
                    'scenario': nome_scenario,
                    'sequenza': seq_chiave,
                    'profitto_netto': kpi['profitto_netto'],
                    'costo_tot': kpi['costo_tot'],
                    'ricavo_tot': kpi['ricavo_tot'],
                    'giorni_arr': kpi['giorni_arr'],
                    'giorni_continui': kpi['giorni_continui'],
                    'qt_netta_q': kpi['qt_netta_q']
                })

    print("Simulazione Monte Carlo completata.")
    # Converte la lista di risultati in un DataFrame Pandas
    return pd.DataFrame(risultati)


def analizza_risultati(df_risultati: pd.DataFrame):
    """
    Stampa un'analisi dei risultati aggregati.
    """
    print("\n--- ANALISI STATISTICA DEI RISULTATI ---")

    # Modifica per NOTA 4: Aggrega anche costo_tot e giorni_arr
    summary = df_risultati.groupby(['scenario', 'sequenza']).agg(
        # Aggregazioni per Profitto
        profitto_media=('profitto_netto', 'mean'),
        profitto_std=('profitto_netto', 'std'),
        profitto_p05=('profitto_netto', lambda x: np.percentile(x, 5)),
        profitto_p95=('profitto_netto', lambda x: np.percentile(x, 95)),

        # Aggregazioni per Costo e Giorni (NOTA 4)
        costo_media=('costo_tot', 'mean'),
        giorni_media=('giorni_arr', 'mean')
    ).reset_index()

    pd.options.display.float_format = '{:,.2f}'.format

    # Modifica per NOTA 3: Rinomina colonne per leggibilità e unità
    summary_print = summary.rename(columns={
        'scenario': 'Scenario',
        'sequenza': 'Sequenza',
        'profitto_media': 'Profitto Medio (€)',
        'profitto_std': 'Profitto Std Dev (€)',
        'profitto_p05': 'Profitto 5° Perc. (€)',
        'profitto_p95': 'Profitto 95° Perc. (€)',
        'costo_media': 'Costo Medio (€)',
        'giorni_media': 'Giorni Medi (arr.)'
    })

    print(summary_print.to_string(index=False))

    # Restituisce il summary con i nomi originali (più facili da processare)
    return summary, summary_print

def salva_risultati_raw(df_risultati: pd.DataFrame, cartella_output: str = "output_csv"):
    """
    Salva il DataFrame dei risultati grezzi in un CSV con timestamp.
    """
    print(f"\nSalvataggio risultati in '{cartella_output}'...")
    try:
        # 2. Crea la cartella se non esiste
        os.makedirs(cartella_output, exist_ok=True)

        # 3. Genera timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # 4. Crea il nome del file
        nome_file = f"run_montecarlo_{timestamp}.csv"
        percorso_file = os.path.join(cartella_output, nome_file)

        # 5. Salva il file
        df_risultati.to_csv(percorso_file, index=False, sep=';', decimal='.')
        print(f"[SUCCESS] Risultati grezzi salvati in: {percorso_file}")

    except Exception as e:
        print(f"[FAIL] Errore durante il salvataggio del file CSV: {e}")


def salva_summary_csv(summary_df: pd.DataFrame, cartella_output: str):
    """
    Salva il DataFrame aggregato in un file CSV con timestamp.
    """
    print(f"\nSalvataggio SUMMARY (statistiche) in '{cartella_output}'...")
    try:
        os.makedirs(cartella_output, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        nome_file = f"run_summary_{timestamp}.csv"
        percorso_file = os.path.join(cartella_output, nome_file)

        # Salva in CSV
        summary_df.to_csv(percorso_file, index=False, sep=';', decimal='.')

        print(f"[SUCCESS] Summary CSV salvato in: {percorso_file}")
    except Exception as e:
        print(f"[FAIL] Errore duringo il salvataggio del summary CSV: {e}")


# --- Esecuzione Principale ---
if __name__ == "__main__":
    try:
        configurazione = carica_config()

        settings = configurazione.get('global_settings', {})
        N_ITERAZIONI = settings.get('n_iterazioni_montecarlo', 1000)
        CARTELLA_OUTPUT = settings.get('cartella_output_csv', 'output_csv_default')  # 'output_csv_default' come fallback

        df_risultati = run_montecarlo(configurazione, N_ITERAZIONI)
        summary_df, summary_print = analizza_risultati(df_risultati)

        salva_risultati_raw(df_risultati, CARTELLA_OUTPUT)
        salva_summary_csv(summary_print, CARTELLA_OUTPUT)

    except Exception as e:
        print(f"\nSimulazione interrotta a causa di un errore: {e}")