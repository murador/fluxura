from pathlib import Path
import xml.etree.ElementTree as ET

from fluxura.config import settings
from fluxura.domain.models import InvoicePayload, InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository

repo = InvoiceRepository()


def generate_fatturapa_xml(data: dict) -> Path:
    payload = InvoicePayload.from_dict(data["payload"])
    totals = data["totali"]

    root = ET.Element("p:FatturaElettronica", attrib={
        "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2",
        "versione": "FPR12",
    })
    body = ET.SubElement(root, "FatturaElettronicaBody")
    dati = ET.SubElement(body, "DatiGenerali")
    dati_doc = ET.SubElement(dati, "DatiGeneraliDocumento")
    ET.SubElement(dati_doc, "Numero").text = payload.numero_fattura
    ET.SubElement(dati_doc, "Data").text = payload.data.isoformat()
    ET.SubElement(dati_doc, "ImportoTotaleDocumento").text = str(totals["totale"])

    output_dir = Path(settings.invoice_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"fattura_{payload.invoice_id}.xml"
    ET.ElementTree(root).write(file_path, encoding="utf-8", xml_declaration=True)

    repo.set_status(payload.invoice_id, InvoiceStatus.XML_GENERATO)
    return file_path
