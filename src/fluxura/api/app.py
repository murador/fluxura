"""API Gateway: riceve le richieste HTTP e accoda la pipeline su Celery.

Nessuna autenticazione per ora.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from fluxura.ingestion.schemas import InvoiceIn
from fluxura.ingestion.sources import InvoiceNotFound, PostgresInvoiceSource
from fluxura.pipeline.tasks import dispatch_invoice_pipeline

app = FastAPI(title="Fluxura API Gateway")


class AcceptedResponse(BaseModel):
    invoice_id: int
    task_id: str
    status: str = "accodata"


@app.post("/invoices", response_model=AcceptedResponse, status_code=202)
def submit_invoice_json(invoice: InvoiceIn) -> AcceptedResponse:
    """Ingestione da messaggio REST/JSON: il payload viaggia nel task."""
    result = dispatch_invoice_pipeline(payload=invoice.to_payload().to_dict())
    return AcceptedResponse(invoice_id=invoice.invoice_id, task_id=result.id)


@app.post("/invoices/{invoice_id}/process", response_model=AcceptedResponse, status_code=202)
def process_invoice_from_db(invoice_id: int) -> AcceptedResponse:
    """Ingestione da Postgres: verifica l'esistenza e accoda per ``invoice_id``."""
    try:
        PostgresInvoiceSource().load(invoice_id)
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = dispatch_invoice_pipeline(invoice_id=invoice_id)
    return AcceptedResponse(invoice_id=invoice_id, task_id=result.id)
