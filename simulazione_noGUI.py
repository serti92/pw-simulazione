# Esegue la simulazione da riga di comando (senza interfaccia grafica)
import app

if __name__ == "__main__":
    try:
        configurazione = app.carica_config()

        settings = configurazione.get('global_settings', {})
        N_ITERAZIONI = settings.get('n_iterazioni_montecarlo', 1000)
        CARTELLA_OUTPUT = settings.get('cartella_output_csv', 'output_csv_default')  # 'output_csv_default' come fallback

        df_risultati = app.run_montecarlo(configurazione, N_ITERAZIONI)
        summary_df, summary_print = app.analizza_risultati(df_risultati)

        app.salva_risultati(df_risultati, summary_print, CARTELLA_OUTPUT)

    except Exception as e:
        print(f"\nSimulazione interrotta a causa di un errore: {e}")