"""Test end-to-end: estrazione -> calcolo -> generazione -> validazione XSD."""

from fluxura.config import settings
from fluxura.services import verification, xml_generation
from fluxura.services.calculation import calculate_totals
from fluxura.services.extraction import extract_invoice
from fluxura.services.verification import validate_xml


def test_generated_xml_passes_xsd(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "invoice_output_dir", str(tmp_path))
    monkeypatch.setattr(verification, "repo", verification.InvoiceRepository())
    monkeypatch.setattr(xml_generation, "repo", xml_generation.InvoiceRepository())

    data = calculate_totals(extract_invoice(7))
    path = xml_generation.generate_fatturapa_xml(data)

    assert path.name == "fattura_7.xml"
    assert validate_xml(path) is True


def test_multiple_vat_rates_and_no_discount(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "invoice_output_dir", str(tmp_path))
    monkeypatch.setattr(verification, "repo", verification.InvoiceRepository())
    monkeypatch.setattr(xml_generation, "repo", xml_generation.InvoiceRepository())

    data = calculate_totals(extract_invoice(8))
    data["payload"]["linee"].append(
        {
            "descrizione": "Libro",
            "quantita": 3,
            "prezzo_unitario": 9.99,
            "aliquota_iva": 4,
            "sconto_percentuale": 0.0,
        }
    )
    path = xml_generation.generate_fatturapa_xml(data)
    assert validate_xml(path) is True