import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import date
import lxml.etree as lxmlET

class DocumentoFatturaElettronica:
    def __init__(self, cedente, destinatario, numero_fattura, linee):
        self.cedente = cedente
        self.destinatario = destinatario
        self.numero_fattura = numero_fattura
        self.linee = linee
        self.data = date.today().isoformat()

    def _crea_elemento_base(self):
        root = ET.Element("p:FatturaElettronica", attrib={
            "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2",
            "versione": "FPR12"
        })
        return root

    def _crea_header(self, root):
        header = ET.SubElement(root, "FatturaElettronicaHeader")

        # Dati Trasmissione
        dati_trasmissione = ET.SubElement(header, "DatiTrasmissione")
        id_trasmittente = ET.SubElement(dati_trasmissione, "IdTrasmittente")
        ET.SubElement(id_trasmittente, "IdPaese").text = "IT"
        ET.SubElement(id_trasmittente, "IdCodice").text = self.cedente["piva"]
        ET.SubElement(dati_trasmissione, "ProgressivoInvio").text = "00001"
        ET.SubElement(dati_trasmissione, "FormatoTrasmissione").text = "FPR12"
        ET.SubElement(dati_trasmissione, "CodiceDestinatario").text = self.destinatario["codice_destinatario"]

        # Cedente Prestatore
        cedente = ET.SubElement(header, "CedentePrestatore")
        dati_anagrafici = ET.SubElement(cedente, "DatiAnagrafici")
        id_fiscale = ET.SubElement(dati_anagrafici, "IdFiscaleIVA")
        ET.SubElement(id_fiscale, "IdPaese").text = "IT"
        ET.SubElement(id_fiscale, "IdCodice").text = self.cedente["piva"]
        anagrafica = ET.SubElement(dati_anagrafici, "Anagrafica")
        ET.SubElement(anagrafica, "Denominazione").text = self.cedente["denominazione"]
        sede = ET.SubElement(cedente, "Sede")
        ET.SubElement(sede, "Indirizzo").text = self.cedente["indirizzo"]
        ET.SubElement(sede, "CAP").text = self.cedente["cap"]
        ET.SubElement(sede, "Comune").text = self.cedente["comune"]
        ET.SubElement(sede, "Provincia").text = self.cedente["provincia"]
        ET.SubElement(sede, "Nazione").text = "IT"

        # Cessionario Committente
        cliente = ET.SubElement(header, "CessionarioCommittente")
        dati_cliente = ET.SubElement(cliente, "DatiAnagrafici")
        id_cliente = ET.SubElement(dati_cliente, "IdFiscaleIVA")
        ET.SubElement(id_cliente, "IdPaese").text = "IT"
        ET.SubElement(id_cliente, "IdCodice").text = self.destinatario["piva"]
        anagrafica_cliente = ET.SubElement(dati_cliente, "Anagrafica")
        ET.SubElement(anagrafica_cliente, "Denominazione").text = self.destinatario["denominazione"]
        sede_cliente = ET.SubElement(cliente, "Sede")
        ET.SubElement(sede_cliente, "Indirizzo").text = self.destinatario["indirizzo"]
        ET.SubElement(sede_cliente, "CAP").text = self.destinatario["cap"]
        ET.SubElement(sede_cliente, "Comune").text = self.destinatario["comune"]
        ET.SubElement(sede_cliente, "Provincia").text = self.destinatario["provincia"]
        ET.SubElement(sede_cliente, "Nazione").text = "IT"

    def _crea_body(self, root):
        body = ET.SubElement(root, "FatturaElettronicaBody")
        dati_generali = ET.SubElement(body, "DatiGenerali")
        dati_doc = ET.SubElement(dati_generali, "DatiGeneraliDocumento")
        ET.SubElement(dati_doc, "TipoDocumento").text = "TD01"
        ET.SubElement(dati_doc, "Divisa").text = "EUR"
        ET.SubElement(dati_doc, "Data").text = self.data
        ET.SubElement(dati_doc, "Numero").text = str(self.numero_fattura)

        beni_servizi = ET.SubElement(body, "DatiBeniServizi")
        totale = 0.0

        for i, linea in enumerate(self.linee, start=1):
            dettaglio = ET.SubElement(beni_servizi, "DettaglioLinee")
            ET.SubElement(dettaglio, "NumeroLinea").text = str(i)
            ET.SubElement(dettaglio, "Descrizione").text = linea["descrizione"]
            ET.SubElement(dettaglio, "Quantita").text = f"{linea['quantita']:.2f}"
            ET.SubElement(dettaglio, "PrezzoUnitario").text = f"{linea['prezzo']:.2f}"
            ET.SubElement(dettaglio, "AliquotaIVA").text = f"{linea['iva']:.2f}"
            totale += linea["prezzo"] * linea["quantita"] * (1 + linea["iva"] / 100)

        pagamento = ET.SubElement(body, "DatiPagamento")
        ET.SubElement(pagamento, "CondizioniPagamento").text = "TP01"
        dettaglio_pagamento = ET.SubElement(pagamento, "DettaglioPagamento")
        ET.SubElement(dettaglio_pagamento, "ModalitaPagamento").text = "MP01"
        ET.SubElement(dettaglio_pagamento, "ImportoPagamento").text = f"{totale:.2f}"

    def genera_xml(self, filename="fattura.xml"):
        root = self._crea_elemento_base()
        self._crea_header(root)
        self._crea_body(root)

        xml_str = ET.tostring(root, encoding="utf-8")
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        print(f"✅ Fattura elettronica salvata in '{filename}'")

    def valida_xml(self, filename="fattura.xml", xsd_path="FatturaElettronica.xsd"):
        try:
            xml_doc = lxmlET.parse(filename)
            xml_schema_doc = lxmlET.parse(xsd_path)
            xml_schema = lxmlET.XMLSchema(xml_schema_doc)
            xml_schema.assertValid(xml_doc)
            print("✅ Validazione XML riuscita secondo lo schema XSD.")
        except lxmlET.DocumentInvalid as e:
            print("❌ Errore di validazione XML:")
            print(e)

# 🔧 Esempio d'uso
if __name__ == "__main__":
    cedente = {
        "denominazione": "Azienda Srl",
        "piva": "01234567890",
        "indirizzo": "Via Roma 1",
        "cap": "67100",
        "comune": "L'Aquila",
        "provincia": "AQ"
    }

    destinatario = {
        "codice_destinatario": "ABC1234",
        "denominazione": "Cliente Spa",
        "piva": "09876543210",
        "indirizzo": "Via Milano 10",
        "cap": "20100",
        "comune": "Milano",
        "provincia": "MI"
    }

    linee = [
        {"descrizione": "Servizio A", "quantita": 2, "prezzo": 50.00, "iva": 22.00},
        {"descrizione": "Prodotto B", "quantita": 1, "prezzo": 100.00, "iva": 22.00}
    ]

    fattura = DocumentoFatturaElettronica(
        cedente=cedente,
        destinatario=destinatario,
        numero_fattura=1,
        linee=linee
    )

    fattura.genera_xml()
    fattura.valida_xml()
