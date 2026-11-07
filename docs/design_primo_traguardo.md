# Design del primo traguardo

## Obiettivo

Rendere affidabile la gestione di una fattura lungo la pipeline Celery,
assicurando che:

1. i calcoli monetari usino precisione decimale e una sola politica di
   arrotondamento;
2. lo stato e gli errori siano persistenti e condivisi tra processi;
3. i test verifichino il percorso integrato dal caricamento della fattura
   all'XML prodotto e allo stato registrato.

Questo traguardo non comprende autenticazione, un'interfaccia di approvazione
umana effettiva, invio PEC/SDI reale o modifiche al deployment. L'eventuale
stato `inviata` non deve essere interpretato come prova di un invio reale:
il mittente attuale è uno stub.

## Situazione di partenza

- [models.py](../src/fluxura/domain/models.py) rappresenta gli importi come
  `float`.
- [schemas.py](../src/fluxura/ingestion/schemas.py) accetta importi e aliquote
  come `float`.
- [calculation.py](../src/fluxura/services/calculation.py) accumula gli
  importi in virgola mobile e arrotonda i totali.
- [xml_generation.py](../src/fluxura/services/xml_generation.py) usa `Decimal`
  e arrotonda gli importi delle righe, quindi applica regole diverse dal
  servizio di calcolo.
- [repository.py](../src/fluxura/infrastructure/repository.py) conserva lo
  stato in memoria e fornisce un payload dimostrativo in caso di fattura
  assente.
- [db.py](../src/fluxura/infrastructure/db.py) configura SQLAlchemy, ma non è
  ancora usato per la persistenza dello stato.
- [tasks.py](../src/fluxura/pipeline/tasks.py) aggiorna lo stato attraverso
  repository in memoria distinti.

## Architettura proposta

```text
API / sorgente PostgreSQL
          │
          ▼
InvoicePayload (valori decimali)
          │
          ▼
Calcolo condiviso ──► risultati decimali serializzati come stringhe
          │                            │
          ▼                            ▼
XML FatturaPA ◄──────────────── task Celery
          │
          ├── file XML su filesystem (comportamento esistente)
          └── repository SQLAlchemy ──► PostgreSQL
                                          stato, errore,
                                          riferimenti e date
```

Il database continua a fornire i dati fattura tramite la sorgente esistente.
La nuova persistenza registra il ciclo di vita, senza introdurre in questo
traguardo una riscrittura dello schema delle fatture sorgenti.

## 1. Modello e politica monetaria

### Tipi

- Usare `Decimal` per prezzo unitario, quantità, aliquota, sconto, imponibili,
  imposte e totali nei modelli e nei servizi Python.
- Accettare valori decimali nello schema Pydantic e applicare lì i vincoli
  d'ingresso. Evitare conversioni intermedie a `float`.
- Per i campi `Numeric` letti da SQLAlchemy, mantenere il valore decimale
  restituito dal driver senza convertirlo in `float`.
- Nei confini JSON della coda Celery serializzare i decimali come stringhe
  decimali; deserializzarli in modo esplicito quando si ricostruiscono i
  modelli. Il formato delle stringhe deve essere stabile e documentato.

### Calcolo condiviso

Introdurre una singola implementazione di calcolo che produca un risultato
tipizzato contenente almeno:

- payload originale normalizzato;
- dettaglio per riga: imponibile e importi richiesti dal documento;
- riepilogo per aliquota IVA: imponibile e imposta;
- totale documento.

Il servizio di calcolo e il generatore XML devono consumare lo stesso risultato
economico. Il generatore può formattare i valori secondo il tracciato, ma non
deve applicare una seconda formula o una politica di arrotondamento
indipendente. La catena Celery deve trasferire il risultato usando il formato
serializzabile definito sopra.

### Politica di arrotondamento da formalizzare

Prima dell'implementazione va confermata con i requisiti contabili/FatturaPA la
regola per:

1. sconto e prezzo della riga;
2. imponibile di riga;
3. aggregazione per aliquota;
4. calcolo e arrotondamento dell'IVA;
5. totale documento e campo `ImportoTotaleDocumento`.

Come base tecnica, la quantizzazione monetaria deve essere centralizzata,
esplicita e coperta da test; non si devono mescolare arrotondamento per riga e
arrotondamento solo sul totale senza una decisione documentata. La modalità
`ROUND_HALF_UP` è già usata dal generatore XML, ma la sua adeguatezza fiscale e
il punto esatto di applicazione devono essere confermati prima di adottarla
come regola condivisa.

## 2. Persistenza e modello dello stato

### Tabella proposta

Introdurre una tabella dedicata, ad esempio `invoice_processing_state`, senza
modificare le tabelle sorgenti `invoices` e `invoice_lines`.

| Campo | Tipo logico | Vincolo / uso |
| --- | --- | --- |
| `invoice_id` | intero | Chiave primaria; identifica la fattura già usata dalla pipeline. |
| `status` | stringa o enum persistito | Stato corrente del ciclo di elaborazione. |
| `error` | testo nullable | Diagnostica dell'ultimo errore, presente solo se applicabile. |
| `xml_path` | testo nullable | Riferimento al file XML generato, non il contenuto del documento. |
| `created_at` | timestamp UTC | Prima registrazione dello stato. |
| `updated_at` | timestamp UTC | Ultima transizione riuscita. |

Per il primo traguardo si propone una riga di stato corrente per fattura,
aggiornata transazionalmente. Una cronologia completa degli eventi e dei retry
può essere aggiunta in seguito se i requisiti di audit la richiedono; non va
simulata sovraccaricando il campo `error`.

Lo stato usa i valori già definiti in `InvoiceStatus`. L'implementazione deve
documentare quali transizioni sono ammesse e come trattare una nuova
elaborazione di una fattura già presente. I retry Celery non devono provocare
un aggiornamento che cancelli un errore utile o faccia avanzare lo stato senza
che la fase corrispondente sia terminata.

### Repository e transazioni

- Sostituire il repository in memoria con un repository SQLAlchemy che riceve
  una factory di sessioni o un'altra dipendenza esplicita, mantenendo i
  dettagli ORM fuori da servizi e task.
- Ogni operazione di lettura/aggiornamento deve avere una sessione con ciclo di
  vita limitato e chiusura garantita anche in caso di errore.
- Aggiornare stato, errore, riferimento XML e timestamp nella stessa
  transazione; fare commit solo dopo un aggiornamento valido e propagare gli
  errori DB al chiamante.
- Prevedere l'inserimento iniziale dello stato in modo concorrente e idempotente:
  due worker che inizializzano la stessa fattura non devono creare righe
  duplicate o sovrascriversi silenziosamente.
- Rimuovere il fallback demo dal percorso operativo. Una fattura non presente
  nella sorgente deve restare un errore esplicito, non produrre dati inventati.
- Evitare di mantenere istanze globali con stato in memoria. I servizi e i task
  devono usare lo stesso backend persistente, anche se vengono eseguiti in
  processi distinti.

### Migrazioni

Adottare Alembic per versionare lo schema applicativo:

1. aggiungere la dipendenza e la configurazione di Alembic;
2. creare una migrazione iniziale per la tabella di stato e i relativi
   vincoli/indici;
3. documentare come applicare le migrazioni a un database nuovo e aggiornare
   uno esistente;
4. verificare migrazione e downgrade in test su PostgreSQL, se il downgrade è
   supportato dal progetto.

Le tabelle demo di ingestione non devono essere ricreate o alterate da questa
migrazione, salvo una decisione separata e documentata.

## 3. Collegamento con la pipeline

Le fasi aggiornano il repository solo dopo il completamento del proprio lavoro:

| Fase | Aggiornamento atteso |
| --- | --- |
| Ingestione | `ESTRATTA` dopo caricamento e validazione del payload. |
| Calcolo | `CALCOLATA` dopo il calcolo riuscito e la produzione del risultato serializzabile. |
| Generazione | `XML_GENERATO` e `xml_path` dopo la scrittura completata del file. |
| Verifica | `VERIFICATA` solo dopo validazione XSD e controlli tecnici superati. |
| Errore | Stato di errore appropriato e diagnostica quando una fase fallisce. |
| Invio | Non attestare un invio reale finché `send_via_pec` resta uno stub. |

Per gli errori di validazione preservare `ERRORE_VALIDAZIONE`. Per gli altri
errori usare `ERRORE` o una classificazione già prevista dal dominio, evitando
di trasformare un errore del database in un errore di fattura non valido.
L'aggiornamento dello stato non deve nascondere l'eccezione originale della
fase.

La pipeline deve poter ripetere una fase in modo controllato: generazione
dello stesso XML e registrazione dello stesso stato non devono creare record
duplicati. La politica per sovrascrivere un XML esistente o ripartire da uno
stato intermedio va definita e testata.

## 4. Piano di test

### Unit test monetari

- Importi con più di due decimali, valori esattamente a metà centesimo e
  quantità frazionarie.
- Sconti ai limiti consentiti e aliquote IVA diverse.
- Riepilogo corretto per aliquota e totale documento.
- Corrispondenza tra risultato del calcolo e valori nel file XML.
- Serializzazione/deserializzazione dei decimali attraverso il confine Celery.
- Rifiuto degli input fuori dai limiti e dei valori non finiti o non validi.

### Test del repository

- Creazione iniziale, lettura e aggiornamento di una fattura.
- Persistenza dopo chiusura e riapertura di una sessione.
- Aggiornamento atomico di stato, errore, percorso XML e timestamp.
- Fattura inesistente, errore di commit e cleanup della sessione.
- Inizializzazione concorrente/idempotente per lo stesso `invoice_id`.
- Vincoli e migrazioni su PostgreSQL.

### Test d'integrazione della pipeline

Usare PostgreSQL di test e un trasporto Celery adatto ai test, senza dipendere
da broker o provider PEC esterni. Eseguire il percorso di ingestione fino alla
verifica e controllare:

- risultato monetario e XML generato;
- stato persistito dopo ogni fase;
- disponibilità dello stato da una sessione distinta;
- comportamento coerente in caso di errore in calcolo, generazione, verifica
  o aggiornamento DB;
- assenza di uno stato finale di successo quando una fase fallisce.

La suite veloce può usare SQLite per i test isolati del repository, ma i test
delle migrazioni, dei tipi `Numeric` e del comportamento concorrente devono
essere eseguiti con PostgreSQL, cioè il database di destinazione.

## 5. Sequenza d'implementazione

1. Confermare la politica fiscale di arrotondamento e il significato degli
   stati, soprattutto retry e rielaborazione.
2. Introdurre tipi decimali e un risultato di calcolo comune; aggiungere test
   unitari prima di collegare la persistenza.
3. Adeguare payload e serializzazione Celery senza usare `float` nei passaggi
   monetari.
4. Definire il modello SQLAlchemy e la migrazione iniziale.
5. Implementare il repository transazionale e i test di persistenza.
6. Collegare i task e i servizi al repository, eliminando il fallback
   dimostrativo.
7. Eseguire i test d'integrazione su PostgreSQL e aggiornare la documentazione
   architetturale in base al comportamento implementato.

## Criteri di accettazione del traguardo

- Tutte le operazioni monetarie sono eseguite con `Decimal`; nessuna fase
  converte gli importi in `float`.
- Una sola politica documentata governa calcolo, riepiloghi IVA e XML.
- Il risultato calcolato e quello rappresentato nell'XML coincidono secondo
  tale politica.
- Gli stati e gli errori sopravvivono al riavvio e sono visibili a worker
  distinti.
- Schema e aggiornamenti sono gestiti con migrazioni e transazioni.
- I test coprono casi limite monetari, persistenza PostgreSQL e percorso
  integrato della pipeline.

## Decisioni da confermare prima di implementare

1. Quale regola contabile/FatturaPA adottare per arrotondare righe, imponibili
   aggregati e imposte, e se `ROUND_HALF_UP` è la modalità richiesta.
2. Se conservare soltanto lo stato corrente oppure richiedere fin da subito
   una tabella di audit degli eventi e dei retry.
3. Come trattare una richiesta di elaborazione ripetuta: ripartire sempre
   dall'ingestione, riprendere da uno stato intermedio o rifiutare le
   transizioni non valide.
