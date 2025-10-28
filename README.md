# 🍇 Simulatore di Vendemmia - Tenuta Pegaso

## 1. Descrizione del Progetto

Questo progetto è uno **strumento di supporto decisionale (Decision Support System, DSS)** progettato per analizzare gli impatti economici e operativi di diversi scenari di vendemmia.

L'applicazione utilizza una **simulazione Monte Carlo** per modellare l'incertezza in variabili chiave (come resa, costi e scarti), fornendo una visione statistica dei possibili risultati (profitto, costi totali, durata della vendemmia).

L'interfaccia utente è costruita con **Streamlit**, rendendo l'analisi complessa accessibile tramite un'applicazione web interattiva.

---

## 2. Architettura del Software

Il progetto adotta un'architettura disaccoppiata che separa l'interfaccia utente (View), la logica di business (Controller) e il motore di calcolo (Model). Questo design garantisce alta manutenibilità, testabilità e flessibilità.

* 📄 **`config.json` (Dati)**
    * File centrale che definisce **tutti** i parametri della simulazione.
    * Contiene scenari (Pessimistico, Reale, Ottimistico), parametri di processo (costi, capacità, scarti), variabili stocastiche (sigma) e impostazioni globali.
    * Il simulatore è **data-driven**: modificando questo file, si modifica l'intero comportamento della simulazione senza toccare il codice.

* 🖥️ **`streamline_app.py` (View)**
    * È l'entry-point dell'applicazione web e gestisce l'interfaccia utente.
    * Controlla la navigazione tra le pagine, gestisce i widget (slider, bottoni, tabelle) e lo stato della sessione (`st.session_state`).
    * Delega tutte le operazioni di calcolo al modulo `app.py`.

* 🖇️ **`app.py` (Controller)**
    * Serve da ponte tra l'interfaccia (`streamline_app.py`) e il motore di calcolo (`simulazione.py`).
    * Contiene le funzioni principali chiamate dall'interfaccia:
        * `carica_config()`: Carica e valida il JSON.
        * `run_montecarlo()`: Esegue il loop principale della simulazione per N iterazioni.
        * `analizza_risultati()`: Aggrega i dati grezzi in un sommario statistico (media, std, percentili).
        * `salva_risultati()`: Esporta i dati in CSV.

* ⚙️ **`simulazione.py` (Model)**
    * È il **cuore del progetto**. Contiene la pura logica di calcolo, senza nessuna dipendenza da Streamlit.
    * Responsabilità principali:
        * `validate_config()`: Una funzione cruciale che esegue la validazione logica dei parametri (es. scarti tra 0 e 1, prezzi positivi), garantendo la robustezza del modello.
        * `gen_random_lotti()`: Genera i lotti d'uva applicando la variabilità stocastica.
        * `run_single_simulation()`: Esegue una singola iterazione di vendemmia, calcolando i KPI (profitto, costi, giorni).

---

## 3. Funzionalità Principali

L'applicazione web (`streamline_app.py`) è suddivisa in tre sezioni funzionali:

### 1. Confronto Scenari
* Esegue la simulazione Monte Carlo completa sui 3 scenari predefiniti (`Pessimistico`, `Reale`, `Ottimistico`) presenti nel `config.json`.
* Mostra una tabella di confronto con i principali indicatori statistici (Profitto Medio, Deviazione Standard, Percentili 5° e 95°).
* Permette il download dei risultati aggregati e dei dati grezzi (RAW) di tutte le N iterazioni.

### 2. Simulatore What-If
* Permette all'utente di selezionare uno scenario di base (es. "Reale").
* Fornisce slider e campi di input per modificare interattivamente i parametri chiave (prezzi, capacità di lavorazione, costi, rese, ecc.).
* L'utente può lanciare una nuova simulazione Monte Carlo con questi parametri personalizzati e visualizzare i risultati, permettendo un'analisi di sensitività immediata.

### 3. Configurazione
* Una pagina di "admin" che permette di modificare direttamente il file `config.json` dall'interfaccia.
* A differenza di un editor di testo grezzo, l'interfaccia è costruita con widget specifici (es. `st.number_input`) che applicano validazioni a front-end (es. `min_value=0.0`, `max_value=1.0` per le percentuali).
* Al salvataggio, il file viene prima validato logicamente da `app.simulazione.validate_config()` per prevenire configurazioni errate.
* Utilizza `st.toast` e `st.session_state` per fornire una notifica di salvataggio "popup" robusta che sopravvive al ricaricamento della pagina.

---

## 4. Installazione e Avvio

### Prerequisiti
* Python (versione 3.9 o superiore consigliata)
* `pip` per la gestione dei pacchetti

### Setup
1.  **Clonare il repository** (o scaricare i file in una cartella).
2.  **Creare un ambiente virtuale** (consigliato):
    ```bash
    python -m venv .venv
    ```
3.  **Attivare l'ambiente virtuale**:
    * Su Windows: `.venv\Scripts\activate`
    * Su macOS/Linux: `source .venv/bin/activate`
4.  **Installare le dipendenze**:
    ```bash
    pip install -r requirements.txt
    ```

### Avvio
L'applicazione può essere eseguita in due modalità:

1.  **Con Interfaccia Grafica (Streamlit)**:
    ```bash
    streamlit run streamline_app.py
    ```
    Aprire il browser all'indirizzo `http://localhost:8501`.

2.  **Senza Interfaccia (Headless/CLI)**:
    Per eseguire la simulazione completa da terminale e salvare i risultati su file (come definito in `config.json`).
    ```bash
    python simulazione_noGUI.py
    ```
    I risultati verranno salvati nella cartella specificata in `config.json` (es. `output_csv/`).

---

## 5. Test e Validazione

Il progetto include una suite di test (`test.py`) per validare il motore di calcolo (`simulazione.py`). Questo garantisce che la logica di business sia corretta e affidabile.

**Per eseguire i test:**
```bash
python test.py
```
La suite di test esegue diverse validazioni critiche:

* **Test di Riproducibilità `(test_seed)`**: Verifica che, a parità di seed, la generazione di lotti casuali sia deterministica e riproducibile.
* **Test di Validazione `(test_val_errori)`**: Assicura che la funzione validate_config blocchi correttamente configurazioni illogiche (es. prezzi negativi, scarti > 100%).
* **Test di Sensitività e Monotonia**:
  * `test_sensitivita_costo`: Verifica che aumentando il costo, il profitto diminuisca.
  * `test_monotonia_scarto`: Verifica che aumentando lo scarto, il profitto diminuisca.
  * `test_sensitivita_prezzo`: Verifica che aumentando i prezzi di vendita, il profitto aumenti.
* **Test Edge Case** `(test_zero_lotti)`: Verifica che se non vengono generati lotti (input 0), tutti i KPI (costi, profitti, giorni) siano 0.

---

## 6. Dipendenze
Il progetto richiede le seguenti librerie Python, definite in `requirements.txt`:

* **pandas**
* **numpy** 
* **streamlit**
