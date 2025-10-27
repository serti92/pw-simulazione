# Motore di calcolo per la simulazione

import math
import random
import numpy as np


def validate_config(config: dict):
    """
    Controlla la validità logica dei parametri chiave nella configurazione.
    Solleva un ValueError se la validazione fallisce.
    """
    print("[Debug] Avvio validazione configurazione...")

    # Controlla kg_per_q
    kg_per_q = config.get('global_settings', {}).get('kg_per_q', 100)
    if kg_per_q <= 0:
        raise ValueError(f"Il parametro 'kg_per_q' deve essere positivo, ma è {kg_per_q}.")

    # Itera su tutti gli scenari ('Pessimistico', 'Reale', 'Ottimistico')
    for scenario_nome, scenario_data in config.get('scenari', {}).items():
        # Controlla i prezzi dei prodotti
        for prodotto in scenario_data.get('prodotti', []):
            prezzo = prodotto.get('prezzo_kg', -1)
            if prezzo <= 0:
                raise ValueError(
                    f"Nel '{scenario_nome}', il prodotto '{prodotto.get('nome')}' ha un prezzo non positivo: {prezzo} €/kg.")

        # Controlla i parametri delle sequenze (manuale, meccanica)
        for seq_chiave in ['manuale', 'meccanica']:
            if seq_chiave in scenario_data:
                params = scenario_data[seq_chiave]
                capacita = params.get('cap_q_gg', -1)
                costo = params.get('costo_euro_gg', -1)
                scarto = params.get('scarto_perc', -1)

                if capacita <= 0:
                    raise ValueError(
                        f"Nel '{scenario_nome}', sequenza '{seq_chiave}', la capacità deve essere positiva, ma è {capacita} q/gg.")
                if costo <= 0:
                    raise ValueError(
                        f"Nel '{scenario_nome}', sequenza '{seq_chiave}', il costo deve essere positivo, ma è {costo} €/gg.")
                if not (0 <= scarto <= 1):
                    raise ValueError(
                        f"Nel '{scenario_nome}', sequenza '{seq_chiave}', lo scarto deve essere tra 0 e 1, ma è {scarto}.")

    print("[Debug] Validazione configurazione completata con successo.")

def set_seed(config: dict):
    """Imposta il seed per la riproducibilità."""
    seed = config.get('global_settings', {}).get('random_seed', 42)
    random.seed(seed)
    np.random.seed(seed)
    print(f"[Debug] Seed impostato a: {seed}")


def get_random_value(base: float, sigma_percent: float, limiti: tuple = (None, None)) -> float:
    """
    Applica una variabilità stocastica a un valore base.
    Genera un valore da una distribuzione normale e applica i limiti
    """
    if sigma_percent == 0:
        return base

    sigma_abs = base * sigma_percent
    val_random = random.normalvariate(base, sigma_abs)

    # Applica limiti
    if limiti[0] is not None:
        val_random = max(limiti[0], val_random)
    if limiti[1] is not None:
        val_random = min(limiti[1], val_random)

    # Non possiamo avere valori negativi per la logica di business
    val_random = max(0, val_random)

    return val_random


def gen_random_lotti(config: dict) -> dict:
    """
    Genera i lotti (in quintali) per i 3 prodotti.
    """
    gen_params = config['par_gen_lotti']
    lotti_gen = {}

    if gen_params['modalita'] == 'resa_ettaro':
        params = gen_params['resa_ettaro']
        sigma_percent = params['resa_sigma_percent']

        for prodotto, superficie in params['superficie_ha'].items():
            resa_media = params['resa_q_ha_media'][prodotto]
            lotto_medio = resa_media * superficie

            # Genera il lotto randomizzato
            lotto_gen = get_random_value(lotto_medio, sigma_percent, (0, None))
            lotti_gen[prodotto] = lotto_gen

    elif gen_params['modalita'] == 'lotto_sigma':
        params = gen_params['lotto_sigma']
        sigma_percent = params['sigma_percent']

        for prodotto, lotto_medio in params['lotto_q_media'].items():
            lotto_gen = get_random_value(lotto_medio, sigma_percent, (0, None))
            lotti_gen[prodotto] = lotto_gen
    else:
        raise ValueError(f"Modalità di generazione lotti '{gen_params['modalita']}' non riconosciuta.")

    return lotti_gen


def run_single_simulation(generated_lots: dict, config_scenario: dict, seq_chiave: str, var_params: dict,
                          global_params: dict) -> dict:
    """
    Esegue una singola iterazione della simulazione per una data sequenza (mauale o automatica)
    """

    # Estrai i parametri
    sequence_params = config_scenario[seq_chiave]
    limiti = global_params.get('validaz_limiti', {}) 
    kg_per_q = global_params.get('kg_per_q', 100)

    # Calcola il lotto totale
    tot_lot_q = sum(generated_lots.values())
    if tot_lot_q == 0:
        return {'giorni_continui': 0, 'giorni_arr': 0, 'costo_tot': 0, 'ricavo_tot': 0,
                'profitto_netto': 0, 'qt_netta_q': 0, 'costo_per_q_netto': 0}

    # Applica variabilità per simulazione Monte Carlo
    capacita_base = sequence_params['cap_q_gg']
    costo_base = sequence_params['costo_euro_gg']
    scarto_base = sequence_params['scarto_perc']

    cap_random = get_random_value(capacita_base, var_params.get('capacita_sigma_percent', 0),
                                               (limiti.get('capacita_min_q_g'), limiti.get('capacita_max_q_g')))
    costo_gg_random = get_random_value(costo_base, var_params.get('costo_sigma_percent', 0),
                                                   (limiti.get('costo_min_euro_g'), limiti.get('costo_max_euro_g')))
    scarto_random = get_random_value(scarto_base, var_params.get('scarto_sigma_percent', 0),
                                             (limiti.get('scarto_min'), limiti.get('scarto_max')))

    # Calcola tempo totale in giorni
    if cap_random == 0: cap_random = 1  # Evita divisione per zero
    giorni_continui = tot_lot_q / cap_random
    giorni_arr = math.ceil(giorni_continui)  # Lavoriamo su giorni interi per semplicità di calcolo costi

    costo_tot = giorni_arr * costo_gg_random

    # Calcola quantità e ricavi netti
    ricavo_tot = 0
    qt_netta_tot_q = 0

    for prod_info in config_scenario['prodotti']:
        nome_prod = prod_info['nome']
        prezzo_kg = prod_info['prezzo_kg']

        if nome_prod in generated_lots:
            qt_lorda_q = generated_lots[nome_prod]
            qt_netta_q = qt_lorda_q * (1 - scarto_random)

            ricavo_prod = qt_netta_q * (prezzo_kg * kg_per_q)  # Converti quintali in kg per determinare il prezzo

            ricavo_tot += ricavo_prod
            qt_netta_tot_q += qt_netta_q

    # Calcola prodotto netto e gli altri KPI
    profitto_netto = ricavo_tot - costo_tot
    costo_per_q_netto = costo_tot / qt_netta_tot_q if qt_netta_tot_q > 0 else 0

    # Restituisci tutti i KPI
    return {
        'giorni_continui': giorni_continui,
        'giorni_arr': giorni_arr,
        'costo_tot': costo_tot,
        'ricavo_tot': ricavo_tot,
        'profitto_netto': profitto_netto,
        'qt_netta_q': qt_netta_tot_q,
        'costo_per_q_netto': costo_per_q_netto
    }