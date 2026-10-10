"""Servizio di generazione XML FatturaPA (tracciato FPR12, conforme a XSD v1.2.2)."""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from lxml import etree

from fluxura.config import settings
from fluxura.domain.models import InvoicePayload, InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository

repo = InvoiceRepository()

NS = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
_CENT = Decimal("0.01")


def _dec(value: float | int | str) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal) -> str:
    return str(value.quantize(_CENT, rounding=ROUND_HALF_UP))


def _add(parent: etree._Element, tag: str, text: str | None = None) -> etree._Element:
    el = etree.SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


def _sede(parent: etree._Element, soggetto: dict) -> None:
    sede = _add(parent, "Sede")
    _add(sede, "Indirizzo", soggetto["indirizzo"])
    _add(sede, "CAP", soggetto["cap"])
    _add(sede, "Comune", soggetto["comune"])
    if soggetto.get("provincia"):
        _add(sede, "Provincia", soggetto["provincia"])
    _add(sede, "Nazione", soggetto.get("nazione", "IT"))


def _dati_anagrafici(parent: etree._Element, soggetto: dict, regime: str | None = None) -> None:
    dati = _add(parent, "DatiAnagrafici")
    fiscale = _add(dati, "IdFiscaleIVA")
    _add(fiscale, "IdPaese", soggetto.get("paese", "IT"))
    _add(fiscale, "IdCodice", soggetto["piva"])
    _add(_add(dati, "Anagrafica"), "Denominazione", soggetto["denominazione"])
    if regime:
        _add(dati, "RegimeFiscale", regime)


def build_fatturapa_tree(payload: InvoicePayload) -> tuple[etree._Element, Decimal]:
    """Costruisce l'albero XML e restituisce anche il totale documento."""
    root = etree.Element(f"{{{NS}}}FatturaElettronica", nsmap={"p": NS}, versione="FPR12")

    header = _add(root, "FatturaElettronicaHeader")
    trasm = _add(header, "DatiTrasmissione")
    id_trasm = _add(trasm, "IdTrasmittente")
    _add(id_trasm, "IdPaese", payload.cedente.get("paese", "IT"))
    _add(id_trasm, "IdCodice", payload.cedente["piva"])
    _add(trasm, "ProgressivoInvio", str(payload.invoice_id)[-10:])
    _add(trasm, "FormatoTrasmissione", "FPR12")
    _add(trasm, "CodiceDestinatario", payload.destinatario.get("codice_destinatario", "0000000"))

    cedente = _add(header, "CedentePrestatore")
    _dati_anagrafici(cedente, payload.cedente, payload.cedente.get("regime_fiscale", "RF01"))
    _sede(cedente, payload.cedente)

    cessionario = _add(header, "CessionarioCommittente")
    _dati_anagrafici(cessionario, payload.destinatario)
    _sede(cessionario, payload.destinatario)

    body = _add(root, "FatturaElettronicaBody")
    beni = etree.Element("DatiBeniServizi")
    riepilogo: dict[Decimal, Decimal] = defaultdict(Decimal)

    for numero, linea in enumerate(payload.linee, start=1):
        qta = _dec(linea.quantita)
        unitario = _dec(linea.prezzo_unitario)
        sconto = _dec(linea.sconto_percentuale)
        totale_linea = (unitario * qta * (1 - sconto / 100)).quantize(_CENT, rounding=ROUND_HALF_UP)
        aliquota = _dec(linea.aliquota_iva).quantize(_CENT)
        riepilogo[aliquota] += totale_linea

        det = _add(beni, "DettaglioLinee")
        _add(det, "NumeroLinea", str(numero))
        _add(det, "Descrizione", linea.descrizione)
        _add(det, "Quantita", _money(qta))
        _add(det, "PrezzoUnitario", _money(unitario))
        if sconto:
            sc = _add(det, "ScontoMaggiorazione")
            _add(sc, "Tipo", "SC")
            _add(sc, "Percentuale", _money(sconto))
        _add(det, "PrezzoTotale", _money(totale_linea))
        _add(det, "AliquotaIVA", _money(aliquota))

    totale_documento = Decimal("0")
    for aliquota, imponibile in sorted(riepilogo.items()):
        imposta = (imponibile * aliquota / 100).quantize(_CENT, rounding=ROUND_HALF_UP)
        totale_documento += imponibile + imposta
        riep = _add(beni, "DatiRiepilogo")
        _add(riep, "AliquotaIVA", _money(aliquota))
        _add(riep, "ImponibileImporto", _money(imponibile))
        _add(riep, "Imposta", _money(imposta))
        _add(riep, "EsigibilitaIVA", "I")

    generali = _add(body, "DatiGenerali")
    doc = _add(generali, "DatiGeneraliDocumento")
    _add(doc, "TipoDocumento", "TD01")
    _add(doc, "Divisa", "EUR")
    _add(doc, "Data", payload.data.isoformat())
    _add(doc, "Numero", payload.numero_fattura)
    _add(doc, "ImportoTotaleDocumento", _money(totale_documento))
    body.append(beni)
    return root, totale_documento


def generate_fatturapa_xml(data: dict) -> Path:
    """Genera l'XML FatturaPA completo e lo salva nel percorso configurato."""
    payload = InvoicePayload.from_dict(data["payload"])
    root, _ = build_fatturapa_tree(payload)

    output_dir = Path(settings.invoice_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"fattura_{payload.invoice_id}.xml"
    etree.ElementTree(root).write(
        str(file_path), encoding="UTF-8", xml_declaration=True, pretty_print=True
    )

    repo.set_status(payload.invoice_id, InvoiceStatus.XML_GENERATO)
    return file_path