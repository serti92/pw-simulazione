# Script per testare il motore di simulazione

import simulazione
import copy
import json

""""# --- MOCK CONFIG ---

MOCK_CONFIG = {
    "global_settings": {
        "random_seed": 42,
        "kg_per_q": 100
    },

    # Per far funzionare run_single_simulation
    "kg_per_q": 100,

    "validaz_limiti": {
        "scarto_min": 0.0, "scarto_max": 0.20,
        "capacita_min_q_g": 10, "capacita_max_q_g": 1000,
        "costo_min_euro_g": 50, "costo_max_euro_g": 5000
    },
    "par_gen_lotti": {
        "modalita": "resa_ettaro",
        "resa_ettaro": {
            "superficie_ha": {"Sangiovese": 6, "Trebbiano": 4, "Merlot": 3},
            "resa_q_ha_media": {"Sangiovese": 85, "Trebbiano": 78, "Merlot": 82},
            "resa_sigma_percent": 0.10
        }
    },
    # Parametri variabilità
    "var_params": {
        "capacita_sigma_percent": 0.0,
        "costo_sigma_percent": 0.0,
        "scarto_sigma_percent": 0.0
    },

    "scenari": {
        "Reale": {
            "prodotti": [
                {"nome": "Sangiovese", "prezzo_kg": 1.10},
                {"nome": "Trebbiano", "prezzo_kg": 0.80},
                {"nome": "Merlot", "prezzo_kg": 0.90}
            ],
            "manuale": {
                "cap_q_gg": 100,
                "costo_euro_gg": 550,
                "scarto_perc": 0.02
            },
            "meccanica": {
                "cap_q_gg": 280,
                "costo_euro_gg": 600,
                "scarto_perc": 0.045
            }
        }
    }
}


# --- FINE MOCK CONFIG --- """

# --- FUNZIONI DI TEST DI VALIDAZIONE ---

def test_seed(config):
    """Test 1: Verifica che il seed garantisca la riproducibilità."""
    print("\n[Test 1] Validazione: Determinismo (Riproducibilità Seed)...")

    # Chiama la funzione corretta dal nostro file
    simulazione.set_seed(config)
    lotti_run1 = simulazione.gen_random_lotti(config)

    simulazione.set_seed(config)  # Resetta lo stesso seed
    lotti_run2 = simulazione.gen_random_lotti(config)

    if lotti_run1 == lotti_run2:
        print("[PASS] I lotti generati sono identici. Il seed funziona.")
        print(f"  Lotti generati: {lotti_run1}")
        return lotti_run1  # Passa i lotti ai test successivi
    else:
        print("[FAIL] I lotti generati sono diversi. Problema con il seed.")
        print(f"  Run 1: {lotti_run1}")
        print(f"  Run 2: {lotti_run2}")
        return None


def test_simulazione_base(lotti_generati, config):
    """Test 2: Esegue e stampa i risultati base (con variabilità a zero)."""
    print("\n[Test 2] Esecuzione Base (Manuale)...")

    # Chiama la funzione di simulazione con i nomi giusti
    kpi_manuale = simulazione.run_single_simulation(
        generated_lots=lotti_generati,
        config_scenario=config['scenari']['Reale'],
        seq_chiave='manuale',
        var_params=config['var_params'],
        global_params=config
    )
    print(f"  PROFITTO NETTO (Base): {kpi_manuale['profitto_netto']:.2f} €")

    print("\n[Test 2] Esecuzione Base (Meccanica)...")
    kpi_meccanica = simulazione.run_single_simulation(
        generated_lots=lotti_generati,
        config_scenario=config['scenari']['Reale'],
        seq_chiave='meccanica',
        var_params=config['var_params'],
        global_params=config
    )
    print(f"  PROFITTO NETTO (Base): {kpi_meccanica['profitto_netto']:.2f} €")
    return kpi_manuale['profitto_netto']  # Ritorna il profitto base per il confronto


def test_sensitivita_costo(lotti_generati, config, profitto_base):
    """Test 3: Verifica che aumentando il costo, il profitto diminuisca."""
    print("\n[Test 3] Validazione: Sensitività Costo (Manuale)...")

    # Crea una copia del config per evitare di modificare l'originale
    config_test = copy.deepcopy(config)

    # Modifica (aumenta) il costo usando le chiavi giuste
    costo_base = config_test['scenari']['Reale']['manuale']['costo_euro_gg']
    config_test['scenari']['Reale']['manuale']['costo_euro_gg'] *= 2  # Raddoppia il costo
    print(f"  Costo base: {costo_base}, Costo test: {config_test['scenari']['Reale']['manuale']['costo_euro_gg']}")

    kpi_test_costo = simulazione.run_single_simulation(
        generated_lots=lotti_generati,
        config_scenario=config_test['scenari']['Reale'],
        seq_chiave='manuale',
        var_params=config_test['var_params'],
        global_params=config_test
    )
    profitto_alto_costo = kpi_test_costo['profitto_netto']
    print(f"  Profitto Base: {profitto_base:.2f} € | Profitto Alto Costo: {profitto_alto_costo:.2f} €")

    if profitto_alto_costo < profitto_base:
        print("[PASS] Aumentando il costo, il profitto è diminuito correttamente.")
    else:
        print("[FAIL] Aumentando il costo, il profitto NON è diminuito.")


def test_monotonia_scarto(lotti_generati, config, profitto_base):
    """Test 4: Verifica che aumentando lo scarto, il profitto diminuisca."""
    print("\n[Test 4] Validazione: Monotonia Scarto (Manuale)...")

    config_test = copy.deepcopy(config)

    # Modifica (aumenta) lo scarto usando le chiavi giuste
    scarto_base = config_test['scenari']['Reale']['manuale']['scarto_perc']
    config_test['scenari']['Reale']['manuale']['scarto_perc'] = 0.5  # Scarto drastico del 50%
    print(f"  Scarto base: {scarto_base}, Scarto test: {config_test['scenari']['Reale']['manuale']['scarto_perc']}")

    kpi_test_scarto = simulazione.run_single_simulation(
        generated_lots=lotti_generati,
        config_scenario=config_test['scenari']['Reale'],
        seq_chiave='manuale',
        var_params=config_test['var_params'],
        global_params=config_test
    )
    profitto_alto_scarto = kpi_test_scarto['profitto_netto']
    # Usa la chiave di output corretta 'qt_netta_q'
    q_netta_alto_scarto = kpi_test_scarto['qt_netta_q']

    print(f"  Profitto Base: {profitto_base:.2f} € | Profitto Alto Scarto: {profitto_alto_scarto:.2f} €")

    if profitto_alto_scarto < profitto_base and q_netta_alto_scarto < sum(lotti_generati.values()):
        print("[PASS] Aumentando lo scarto, il profitto e la quantità netta sono diminuiti.")
    else:
        print("[FAIL] Aumentando lo scarto, il profitto o la quantità non sono diminuiti.")


def test_sensitivita_prezzo(lotti_generati, config, profitto_base):
    """Test 5: Verifica che aumentando il prezzo di vendita, il profitto aumenti."""
    print("\n[Test 5] Validazione: Sensitività Prezzo (Manuale)...")

    config_test = copy.deepcopy(config)

    # Aumentiamo il prezzo del primo prodotto (Sangiovese)
    prezzo_base = config_test['scenari']['Reale']['prodotti'][0]['prezzo_kg']
    config_test['scenari']['Reale']['prodotti'][0]['prezzo_kg'] *= 2
    print(
        f"  Prezzo base (Sang.): {prezzo_base}, Prezzo test: {config_test['scenari']['Reale']['prodotti'][0]['prezzo_kg']}")

    kpi_test_prezzo = simulazione.run_single_simulation(
        generated_lots=lotti_generati,
        config_scenario=config_test['scenari']['Reale'],
        seq_chiave='manuale',
        var_params=config_test['var_params'],
        global_params=config_test
    )
    profitto_alto_prezzo = kpi_test_prezzo['profitto_netto']
    print(f"  Profitto Base: {profitto_base:.2f} € | Profitto Alto Prezzo: {profitto_alto_prezzo:.2f} €")

    if profitto_alto_prezzo > profitto_base:
        print("[PASS] Aumentando il prezzo, il profitto è aumentato correttamente.")
    else:
        print("[FAIL] Aumentando il prezzo, il profitto NON è aumentato.")


def test_zero_lotti(config):
    """Test 6: Verifica che con lotti a zero, i KPI siano zero."""
    print("\n[Test 6] Validazione: Lotti a 0...")

    lotti_vuoti = {"Sangiovese": 0, "Trebbiano": 0, "Merlot": 0}

    kpi_zero = simulazione.run_single_simulation(
        generated_lots=lotti_vuoti,
        config_scenario=config['scenari']['Reale'],
        seq_chiave='manuale',
        var_params=config['var_params'],
        global_params=config
    )

    # Verifichiamo che i KPI principali siano 0
    if kpi_zero['profitto_netto'] == 0 and kpi_zero['costo_tot'] == 0 and kpi_zero['giorni_arr'] == 0:
        print("[PASS] Con lotti a zero, tutti i KPI principali sono 0.")
    else:
        print(f"[FAIL] Con lotti a zero, i KPI non sono corretti: {kpi_zero}")


def test_val_errori(config):
    """Test 7: Verifica che la funzione validate_config blocchi configurazioni errate."""
    print("\n[Test 7] Validazione: Rilevamento Errori Config...")

    test_superati = 0
    num_test = 3  # Numero di sotto-test che faremo

    # Test 7.1: Prezzo negativo
    try:
        config_test = copy.deepcopy(config)
        config_test['scenari']['Reale']['prodotti'][0]['prezzo_kg'] = -10
        simulazione.validate_config(config_test)
        # Se arriviamo qui, il test è fallito perché non ha sollevato l'errore
        print("[FAIL] validate_config non ha bloccato un prezzo negativo.")
    except ValueError as e:
        print("[PASS] validate_config ha bloccato correttamente un prezzo negativo.")
        test_superati += 1
    except Exception as e:
        print(f"[FAIL] Errore inatteso nel test prezzo: {e}")

    # Test 7.2: Scarto > 1
    try:
        config_test = copy.deepcopy(config)
        config_test['scenari']['Reale']['manuale']['scarto_perc'] = 1.5  # Scarto al 150%
        simulazione.validate_config(config_test)
        print("[FAIL] validate_config non ha bloccato uno scarto > 1.")
    except ValueError as e:
        print("[PASS] validate_config ha bloccato correttamente uno scarto > 1.")
        test_superati += 1
    except Exception as e:
        print(f"[FAIL] Errore inatteso nel test scarto: {e}")

    # Test 7.3: Capacità negativa
    try:
        config_test = copy.deepcopy(config)
        config_test['scenari']['Reale']['meccanica']['cap_q_gg'] = -100
        simulazione.validate_config(config_test)
        print("[FAIL] validate_config non ha bloccato una capacità negativa.")
    except ValueError as e:
        print("[PASS] validate_config ha bloccato correttamente una capacità negativa.")
        test_superati += 1
    except Exception as e:
        print(f"[FAIL] Errore inatteso nel test capacità: {e}")

    return test_superati == num_test

# --- FUNZIONE PRINCIPALE DI TEST ---
def main():
    """Funzione principale per eseguire tutti i test."""

    print("--- AVVIO TEST PER SIMULAZIONE.PY ---")

    # Carica il file JSON
    try:
        with open('config.json', 'r') as f:
            CONFIG_JSON = json.load(f)
        print("[Info] File 'config.json' caricato con successo.")
    except FileNotFoundError:
        print("[FAIL] File 'config.json' non trovato. Assicurati che sia nella stessa cartella.")
        return
    except json.JSONDecodeError:
        print("[FAIL] Errore nella lettura del JSON. Controlla la sintassi del file.")
        return

    # Cerca kg_per_q in global_settings e al primo livello.
    if 'global_settings' in CONFIG_JSON and 'kg_per_q' in CONFIG_JSON['global_settings']:
        CONFIG_JSON['kg_per_q'] = CONFIG_JSON['global_settings']['kg_per_q']

    # Blocco per catturare errori di validazione
    try:
        # Per prima cosa, testiamo che la validazione funzioni
        print("\n[Test 0] Validazione Configurazione Iniziale...")
        simulazione.validate_config(CONFIG_JSON)
        print("[PASS] La configurazione JSON è stata validata.")
    except ValueError as e:
        print(f"[FAIL] Validazione fallita: {e}")
        return  # Esce se la config base non è valida

    # Test: Testiamo che la validazione blocchi i dati errati
    if not test_val_errori(CONFIG_JSON):
        print("\nTest falliti (Validazione Errori). Uscita.")
        return

    # Test 1: Determinismo
    lotti = test_seed(CONFIG_JSON)

    if lotti is None:
        print("\nTest falliti (Seed). Uscita.")
        return

    # Test 2: Simulazione Base
    profitto_base_man = test_simulazione_base(lotti, CONFIG_JSON)

    # Test 3: Sensitività Costo
    test_sensitivita_costo(lotti, CONFIG_JSON, profitto_base_man)

    # Test 4: Monotonia Scarto
    test_monotonia_scarto(lotti, CONFIG_JSON, profitto_base_man)

    # Test 5: Sensitività Prezzo
    test_sensitivita_prezzo(lotti, CONFIG_JSON, profitto_base_man)

    # Test 6: Edge Case Lotti a Zero
    test_zero_lotti(CONFIG_JSON)

    print("\n--- TEST COMPLETATI ---")


if __name__ == "__main__":
    main()