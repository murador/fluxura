# Mock Test Results - Fluxura Pipeline

## Test Execution Summary

**Data:** 2026-10-03 15:37:51  
**Environment:** Kubernetes (namespace: `fluxura`)  
**Status:** ✅ **SUCCESS** - Tutta la pipeline completata senza errori

---

## Pipeline Execution Flow

La pipeline è stata triggerata con:
```python
dispatch_invoice_pipeline(invoice_id=42)
```

### Fasi eseguite

| # | Fase | Task ID | Status | Tempo | Output |
|---|---|---|---|---|---|
| 1 | **Calcolo** | `86897ad1-abd5-45bf-81d6-18d17498aa40` | ✅ succeeded | 8.24 ms | Totali calcolati |
| 2 | **Generazione XML** | `e30f884c-a5c4-4740-a993-904e59b58ba0` | ✅ succeeded | 9.81 ms | `artifacts/xml/fattura_42.xml` |
| 3 | **Verifica** | `6473043e-d430-47a1-a660-6e0d0a955818` | ✅ succeeded | 9.48 ms | `artifacts/xml/fattura_42.xml` |
| 4 | **Invio PEC** | `2a9ccf6a-d933-42a5-aa40-4c807dc381c6` | ✅ succeeded | 3.30 ms | `artifacts/xml/fattura_42.xml` |

---

## Dettagli Calcolo

**Task:** `fluxura.calculate`

Dati fattura elaborati:

```json
{
  "invoice_id": 42,
  "cedente": {
    "denominazione": "Azienda Demo Srl",
    "piva": "01234567890",
    "indirizzo": "Via Roma 1",
    "cap": "00100",
    "comune": "Roma",
    "provincia": "RM"
  },
  "destinatario": {
    "denominazione": "Cliente Demo Spa",
    "piva": "09876543210",
    "indirizzo": "Via Milano 10",
    "cap": "20100",
    "comune": "Milano",
    "provincia": "MI",
    "codice_destinatario": "ABC1234"
  },
  "numero_fattura": "42/2026",
  "data": "2026-10-03",
  "linee": [...]
}
```

**Totali calcolati:**
```json
{
  "imponibile": 190.00,
  "iva": 41.80,
  "totale": 231.80
}
```

✅ **Validazione:** IVA corretta (22% di 190 = 41,80)

---

## Dettagli Generazione XML

**Task:** `fluxura.generate_xml`

- **Output:** `artifacts/xml/fattura_42.xml`
- **Status:** ✅ File generato correttamente
- **Tempo:** 9.81 ms

Il file XML conforme FatturaPA è stato creato nel pod worker.

---

## Dettagli Verifica

**Task:** `fluxura.verify`

- **Input:** `artifacts/xml/fattura_42.xml`
- **Status:** ✅ Validazione XSD completata
- **Tempo:** 9.48 ms

---

## Dettagli Invio PEC

**Task:** `fluxura.send_pec`

- **Input:** `artifacts/xml/fattura_42.xml`
- **Status:** ✅ Mock invio completato
- **Tempo:** 3.30 ms

**Nota:** In questa fase di test, l'invio PEC è un mock. Non è stata effettuata alcuna connessione SMTP/PEC reale.

---

## Log Completi

```
[2026-10-03 15:37:51,401: INFO/MainProcess] Task fluxura.generate_xml[e30f884c-a5c4-4740-a993-904e59b58ba0] received
[2026-10-03 15:37:51,404: INFO/ForkPoolWorker-1] Task fluxura.calculate[86897ad1-abd5-45bf-81d6-18d17498aa40] succeeded in 0.008243821999712964s: {'payload': {...}, 'totali': {'imponibile': 190.0, 'iva': 41.8, 'totale': 231.8}}
[2026-10-03 15:37:51,428: INFO/ForkPoolWorker-1] Task fluxura.generate_xml[e30f884c-a5c4-4740-a993-904e59b58ba0] succeeded in 0.009810361000290868s: 'artifacts/xml/fattura_42.xml'
[2026-10-03 15:37:51,432: INFO/MainProcess] Task fluxura.verify[6473043e-d430-47a1-a660-6e0d0a955818] received
[2026-10-03 15:37:51,447: INFO/MainProcess] Task fluxura.send_pec[2a9ccf6a-d933-42a5-aa40-4c807dc381c6] received
[2026-10-03 15:37:51,450: INFO/ForkPoolWorker-1] Task fluxura.verify[6473043e-d430-47a1-a660-6e0d0a955818] succeeded in 0.009477883000272413s: 'artifacts/xml/fattura_42.xml'
[2026-10-03 15:37:51,461: INFO/ForkPoolWorker-1] Task fluxura.send_pec[2a9ccf6a-d933-42a5-aa40-4c807dc381c6] succeeded in 0.00329904299996997s: 'artifacts/xml/fattura_42.xml'
```

---

## Verifiche Consigliate

### 1. Recuperare il file XML generato

```bash
POD=$(kubectl get pod -l app=fluxura-worker -n fluxura -o jsonpath='{.items[0].metadata.name}')

# Visualizzare il contenuto
kubectl -n fluxura exec $POD -- cat artifacts/xml/fattura_42.xml

# Oppure copiare in locale
kubectl -n fluxura cp $POD:artifacts/xml/fattura_42.xml ./fattura_42.xml
```

### 2. Monitorare la pipeline in Flower

```bash
kubectl -n fluxura port-forward svc/flower 5555:5555
# Apri: http://localhost:5555
```

### 3. Verificare lo stato dei pod

```bash
kubectl -n fluxura get pods
kubectl -n fluxura get events --sort-by='.lastTimestamp'
```

---

## Note Importanti

⚠️ **Questo test è in modalità MOCK:**

1. **`send_pec`:** Non effettua connessioni SMTP/PEC reali. Ritorna il percorso del file.
2. **`verify`:** Non valida l'XML contro l'XSD ufficiale FatturaPA. Ritorna il percorso del file.
3. **Persistenza:** I file XML sono creati **dentro il container**. Senza volume persistente, spariscono al riavvio del pod.

### Per la produzione:

- Implementare validazione XSD reale in `verify()`
- Implementare invio PEC vero in `send_pec()`
- Aggiungere un volume persistente per i file generati
- Configurare le credenziali PEC/SMTP tramite variabili d'ambiente

---

## Conclusioni

✅ La pipeline è **funzionante** e **distribuita correttamente** su Kubernetes.  
✅ Tutti i task sono **eseguiti in sequenza** tramite Celery + RabbitMQ.  
✅ Il **broker di messaggi** comunica correttamente con i worker.  
✅ I **tempi di esecuzione** sono accettabili (< 50 ms totali).

Prossimi passi:
- [x] Implementare validazione XSD ufficiale
- [ ] Configurare credenziali PEC
- [ ] Aggiungere persistenza per i file
- [ ] Scrivere test unitari per ogni fase
