# Piano delle modifiche ad alta priorità

Questo documento descrive esclusivamente gli interventi della **priorità 1**:

1. rendere precisi e coerenti i calcoli monetari;
2. rendere persistenti gli stati e gli errori delle fatture.

L'obiettivo è sostituire i comportamenti dimostrativi attuali con una base
affidabile e verificabile, senza includere in questo piano le altre priorità
del progetto, come autenticazione, deployment o invio PEC reale.

## 1. Calcoli monetari affidabili

### Situazione attuale

`InvoiceLine` e lo schema d'ingresso rappresentano quantità, prezzi e aliquote
come `float`. Il servizio di calcolo accumula imponibile e IVA in virgola
mobile e arrotonda i totali alla fine. La generazione XML converte invece i
valori in `Decimal` e arrotonda il totale di ciascuna riga. I due percorsi
possono quindi produrre risultati diversi per importi con frazioni di centesimo.

### Modifiche da fare

1. **Definire e documentare la politica di arrotondamento**
   - Stabilire quando arrotondare gli importi di riga, le basi imponibili per
     aliquota, l'IVA e il totale documento.
   - Verificare che la politica sia coerente con il tracciato FatturaPA e con
     i requisiti contabili del progetto.
   - Usare la stessa politica nel calcolo e nella generazione XML.

2. **Adottare `Decimal` per gli importi**
   - Aggiornare i modelli e la validazione d'ingresso affinché i valori
     monetari non vengano convertiti prematuramente in `float`.
   - Costruire i valori decimali da stringhe o da rappresentazioni decimali
     affidabili, evitando conversioni dirette da numeri binari in virgola
     mobile.
   - Applicare una modalità di arrotondamento esplicita e una quantizzazione
     centralizzata alla precisione richiesta.
   - Conservare la compatibilità della serializzazione JSON tra i task Celery,
     convertendo i decimali in stringhe o in un formato concordato e
     ricostruendoli in modo controllato.

3. **Allineare calcolo e XML**
   - Riutilizzare le stesse regole per sconti, quantità, imponibile e IVA in
     tutte le fasi.
   - Evitare che la generazione XML ricalcoli importi con criteri diversi
     rispetto al servizio di calcolo; il dato usato nel documento deve
     corrispondere al risultato verificato dalla pipeline.
   - Mantenere invariato il formato richiesto dai campi XML e validare il
     documento con gli XSD inclusi nel progetto.

4. **Ampliare i test**
   - Aggiungere casi con prezzi e quantità che producono frazioni di centesimo,
     sconti, più aliquote IVA e valori ai limiti di arrotondamento.
   - Verificare esplicitamente imponibile, IVA e totale, non soltanto la
     validità XSD.
   - Verificare che i totali calcolati coincidano con quelli rappresentati
     nell'XML.
   - Aggiungere test di serializzazione e deserializzazione dei valori
     decimali attraverso il formato usato dai task Celery.

### Criteri di completamento

- I risultati monetari non dipendono da artefatti della virgola mobile.
- Calcolo e generazione XML condividono una politica di arrotondamento
  documentata e producono importi coerenti.
- I test coprono i casi limite concordati e continuano a validare l'XML contro
  lo schema FatturaPA incluso.

## 2. Persistenza dello stato della fattura

### Situazione attuale

`InvoiceRepository` mantiene stato ed errori in un dizionario in memoria e
restituisce dati dimostrativi se la fattura non è presente. Le fasi della
pipeline istanziano repository distinti; pertanto lo stato non è condiviso in
modo affidabile tra processi o worker e si perde al riavvio. È presente un
bootstrap SQLAlchemy, ma non una persistenza transazionale dello stato né un
sistema di migrazioni.

### Modifiche da fare

1. **Definire il modello persistente del ciclo di vita**
   - Stabilire quali informazioni memorizzare per ogni fattura: identificativo,
     stato corrente, eventuale errore, date di creazione e aggiornamento e
     riferimento all'XML generato.
   - Definire vincoli e indici appropriati, compresa l'unicità
     dell'identificativo fattura.
   - Decidere come registrare gli errori e i tentativi in modo da poter
     ricostruire l'esito delle singole fasi senza conservare dati non
     necessari.

2. **Aggiungere migrazioni del database**
   - Introdurre uno strumento di migrazione compatibile con SQLAlchemy.
   - Creare una migrazione iniziale per le tabelle dello stato e applicarla in
     modo ripetibile negli ambienti di sviluppo e test.
   - Documentare come applicare le migrazioni e come portare il database a una
     versione precedente, se supportato.

3. **Sostituire il repository in memoria**
   - Implementare le operazioni di lettura e aggiornamento dello stato usando
     sessioni SQLAlchemy e transazioni.
   - Rimuovere il fallback dimostrativo dal percorso operativo: una fattura
     assente deve produrre un errore esplicito, non un payload inventato.
   - Definire la gestione delle sessioni e la chiusura delle risorse in modo
     sicuro anche quando un'operazione fallisce.
   - Mantenere un'interfaccia repository chiara, così servizi e task non
     dipendano direttamente dai dettagli SQLAlchemy.

4. **Collegare la persistenza a tutte le fasi**
   - Aggiornare i punti della pipeline che registrano estrazione, calcolo,
     generazione XML, verifica, invio ed errori affinché usino il repository
     persistente.
   - Registrare gli errori con un messaggio diagnostico utile, evitando che un
     aggiornamento fallito venga ignorato o presentato come successo.
   - Assicurare che lo stato osservato da un worker sia visibile agli altri
     worker e resti disponibile dopo il riavvio dell'applicazione.
   - Definire transizioni di stato valide e il comportamento per retry e
     rielaborazioni, così che un nuovo tentativo non cancelli informazioni
     utili o lasci la fattura in uno stato incoerente.

5. **Verificare il comportamento con test**
   - Aggiungere test del repository per creazione, lettura, aggiornamento,
     gestione errori e fattura inesistente.
   - Verificare la persistenza dopo la chiusura e riapertura di una sessione.
   - Aggiungere test d'integrazione con PostgreSQL per migrazioni,
     transazioni e aggiornamenti eseguiti da sessioni distinte.
   - Verificare che i task della pipeline aggiornino gli stati attesi e che un
     errore non venga registrato come completamento riuscito.

### Criteri di completamento

- Lo stato della fattura è conservato in PostgreSQL e condiviso tra processi e
  worker.
- Migrazioni ripetibili creano lo schema necessario senza dipendere dagli
  script di seed dimostrativi.
- Le fasi della pipeline usano il repository persistente e segnalano
  esplicitamente gli errori di persistenza.
- Test unitari e d'integrazione verificano gli aggiornamenti di stato, la
  gestione degli errori e la persistenza tra sessioni.

## Sequenza consigliata

1. Concordare e documentare la politica di arrotondamento.
2. Aggiornare i tipi monetari e i test di calcolo/serializzazione/XML.
3. Definire schema persistente e migrazioni per lo stato.
4. Implementare il repository transazionale e collegarlo a tutte le fasi.
5. Eseguire i test unitari e d'integrazione e aggiornare la documentazione
   architetturale in base al comportamento effettivamente realizzato.
