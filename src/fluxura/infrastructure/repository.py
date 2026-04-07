"""Repository in-memory di esempio.

Questo file simula persistenza e stato fattura in attesa di integrazione
con veri modelli SQLAlchemy.
"""

from datetime import datetime

from fluxura.domain.models import InvoiceStatus


class InvoiceRepository:
    """Repository placeholder per integrare SQLAlchemy models reali."""

    def __init__(self):
        # Stato volatile in memoria, indicizzato per ``invoice_id``.
        self._state: dict[int, dict] = {}

    def load_subject_invoice(self, invoice_id: int) -> dict:
        """Carica una fattura candidata; se assente ritorna un dataset demo."""
        return self._state.get(
            invoice_id,
            {
                "invoice_id": invoice_id,
                "cedente": {
                    "denominazione": "Azienda Demo Srl",
                    "piva": "01234567890",
                    "indirizzo": "Via Roma 1",
                    "cap": "00100",
                    "comune": "Roma",
                    "provincia": "RM",
                },
                "destinatario": {
                    "denominazione": "Cliente Demo Spa",
                    "piva": "09876543210",
                    "indirizzo": "Via Milano 10",
                    "cap": "20100",
                    "comune": "Milano",
                    "provincia": "MI",
                    "codice_destinatario": "ABC1234",
                },
                "linee": [
                    {
                        "descrizione": "Consulenza",
                        "quantita": 2,
                        "prezzo_unitario": 100,
                        "aliquota_iva": 22,
                        "sconto_percentuale": 5,
                    }
                ],
                "numero_fattura": f"{invoice_id}/2026",
            },
        )

    def set_status(self, invoice_id: int, status: InvoiceStatus, error: str | None = None) -> None:
        """Aggiorna stato di avanzamento, eventuale errore e timestamp UTC."""
        state = self._state.setdefault(invoice_id, {})
        state["status"] = status.value
        state["error"] = error
        state["updated_at"] = datetime.utcnow().isoformat()
