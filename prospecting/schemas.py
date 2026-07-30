from datetime import date, datetime

from pydantic import BaseModel

from prospecting.models import ProspectSource, ProspectStatus, Segment


class ProspectCreate(BaseModel):
    company_name: str
    segment: Segment = Segment.outro
    size_estimate: str | None = None
    source: ProspectSource = ProspectSource.outro
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    signals: str | None = None
    notes: str | None = None
    week: date | None = None


class ProspectUpdate(BaseModel):
    company_name: str | None = None
    segment: Segment | None = None
    size_estimate: str | None = None
    source: ProspectSource | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    signals: str | None = None
    status: ProspectStatus | None = None
    discard_reason: str | None = None
    notes: str | None = None
    contacted_at: date | None = None


class ProspectOut(ProspectCreate):
    id: int
    status: ProspectStatus
    discard_reason: str | None = None
    contacted_at: date | None = None
    lead_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConvertToLead(BaseModel):
    """Payload para converter prospect em lead no CRM."""
    contact_name: str
    phone: str | None = None
    email: str | None = None
    notes: str | None = None


class WeeklyStats(BaseModel):
    week: date
    pesquisando: int
    qualificado: int
    contactado: int
    convertido: int
    descartado: int
    total: int
    meta_pesquisadas: int = 20
    meta_contactadas: int = 10
