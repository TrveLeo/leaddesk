from datetime import date, datetime

from pydantic import BaseModel

from crm.models import InteractionType, Source, Stage


class InteractionCreate(BaseModel):
    type: InteractionType = InteractionType.mensagem
    description: str
    date: date


class InteractionOut(InteractionCreate):
    id: int
    lead_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadCreate(BaseModel):
    company_name: str
    contact_name: str
    phone: str | None = None
    email: str | None = None
    source: Source = Source.outro
    stage: Stage = Stage.novo_contato
    notes: str | None = None
    next_action: str | None = None
    next_action_date: date | None = None


class LeadUpdate(BaseModel):
    company_name: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: Source | None = None
    stage: Stage | None = None
    notes: str | None = None
    next_action: str | None = None
    next_action_date: date | None = None


class LeadOut(LeadCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    interactions: list[InteractionOut] = []

    model_config = {"from_attributes": True}


class LeadSummary(BaseModel):
    id: int
    company_name: str
    contact_name: str
    stage: Stage
    source: Source
    next_action: str | None
    next_action_date: date | None
    interaction_count: int = 0

    model_config = {"from_attributes": True}
