# Schemi XSD FatturaPA

Schemi usati da `fluxura.services.verification` per la validazione degli XML.

| File | Origine | Versione |
|------|---------|----------|
| `Schema_del_file_xml_FatturaPA_v1.2.2.xsd` | Agenzia delle Entrate (fatturapa.gov.it) | 1.2.2 |
| `xmldsig-core-schema.xsd` | W3C, REC-xmldsig-core-20020212 | 2002-02-12 |

## Modifica locale

Nell'XSD FatturaPA l'`schemaLocation` dell'`xs:import` di xmldsig è stato cambiato da
`http://www.w3.org/TR/2002/REC-xmldsig-core-20020212/xmldsig-core-schema.xsd`
a `xmldsig-core-schema.xsd`, per validare offline (il parser ha `no_network=True`).
Nessun'altra modifica.

SHA256 dell'XSD FatturaPA prima della modifica (blob git del primo commit):
`b46ad814fd558863f12184614cce0e1d8fe7a45ea9a05110dff834248ada2379` (commit `78cbe5b`).

## Integrità

`CHECKSUMS.sha256` contiene gli hash dei file in uso; `tests/test_schema_checksums.py`
li verifica. Gli hash proteggono da modifiche accidentali, non dimostrano
l'autenticità: l'Agenzia non pubblica checksum ufficiali. I file `.xsd` sono
marcati `-text` in `.gitattributes` per evitare conversioni di fine riga che ne
cambierebbero l'hash.

## Aggiornare lo schema

1. Scaricare la nuova versione dal sito ufficiale e verificarne la provenienza.
2. Salvarla in questa cartella e annotare l'hash dell'originale scaricato.
3. Ripetere la modifica dell'`schemaLocation` descritta sopra.
4. Aggiornare `DEFAULT_XSD_PATH` in `services/verification.py` e, se cambiano
   namespace o tracciato, `NS` e il generatore in `services/xml_generation.py`.
5. Rigenerare i checksum (`sha256sum *.xsd > CHECKSUMS.sha256`, oppure
   `Get-FileHash` su PowerShell nel formato `<hash>  <file>`).
6. Eseguire `pytest` e fare commit indicando la versione della specifica.