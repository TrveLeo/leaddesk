from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from crm.database import get_db
from crm.models import Lead, Stage
from crm.schemas import LeadCreate, LeadOut, LeadSummary, LeadUpdate

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/", response_model=list[LeadSummary])
def list_leads(stage: Stage | None = None, db: Session = Depends(get_db)):
    q = select(Lead)
    if stage:
        q = q.where(Lead.stage == stage)
    q = q.order_by(Lead.next_action_date.asc().nullslast(), Lead.updated_at.desc())
    leads = db.scalars(q).all()
    result = []
    for lead in leads:
        summary = LeadSummary(
            id=lead.id,
            company_name=lead.company_name,
            contact_name=lead.contact_name,
            stage=lead.stage,
            source=lead.source,
            next_action=lead.next_action,
            next_action_date=lead.next_action_date,
            interaction_count=len(lead.interactions),
        )
        result.append(summary)
    return result


@router.post("/", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.scalar(
        select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.interactions))
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    db.delete(lead)
    db.commit()


@router.get("/pipeline/summary")
def pipeline_summary(db: Session = Depends(get_db)):
    leads = db.scalars(select(Lead)).all()
    summary = {stage.value: 0 for stage in Stage}
    for lead in leads:
        summary[lead.stage.value] += 1
    return summary
