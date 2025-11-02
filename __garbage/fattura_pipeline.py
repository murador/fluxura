from prefect import flow, task, pause_flow_run
from fattura_elettronica import DocumentoFatturaElettronica
from db import estrai_dati, calcola_importi, salva_xml, invia_pec

@task
def estrazione(soggetto_id):
    return estrai_dati(soggetto_id)

@task
def calcolo(dati):
    return calcola_importi(dati)

@task
def generazione(dati_calcolati):
    fattura = DocumentoFatturaElettronica(**dati_calcolati)
    filename = f"fattura_{dati_calcolati['id']}.xml"
    fattura.genera_xml(filename)
    return filename

@task
def verifica(filename):
    # Validazione XSD
    approvata = DocumentoFatturaElettronica.valida_xml(filename)
    if not approvata:
        raise ValueError("Fattura non valida")
    # Pausa per approvazione manuale
    pause_flow_run(wait_for_input=True)
    return True

@task
def invio(filename):
    invia_pec(filename)

@flow(name="Pipeline Fattura Elettronica")
def pipeline_fattura(soggetto_id: int):
    dati = estrazione(soggetto_id)
    importi = calcolo(dati)
    xml_file = generazione(importi)
    if verifica(xml_file):
        invio(xml_file)

# Esecuzione manuale
if __name__ == "__main__":
    pipeline_fattura(soggetto_id=123)
