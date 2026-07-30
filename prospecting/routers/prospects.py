from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from crm.database import get_db
from crm.models import Lead, Source, Stage
from prospecting.models import Prospect, ProspectStatus
from prospecting.schemas import (
    ConvertToLead,
    ProspectCreate,
    ProspectOut,
    ProspectUpdate,
    WeeklyStats,
)

router = APIRouter(prefix="/prospects", tags=["prospects"])


def _current_week_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


@router.get("/", response_model=list[ProspectOut])
def list_prospects(
    status: ProspectStatus | None = None,
    week: date | None = None,
    db: Session = Depends(get_db),
):
    q = select(Prospect)
    if status:
        q = q.where(Prospect.status == status)
    if week:
        q = q.where(Prospect.week == week)
    q = q.order_by(Prospect.created_at.desc())
    return db.scalars(q).all()


@router.post("/", response_model=ProspectOut, status_code=201)
def create_prospect(payload: ProspectCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if not data.get("week"):
        data["week"] = _current_week_monday()
    prospect = Prospect(**data)
    db.add(prospect)
    db.commit()
    db.refresh(prospect)
    return prospect


@router.get("/week/stats", response_model=WeeklyStats)
def weekly_stats(week: date | None = None, db: Session = Depends(get_db)):
    target_week = week or _current_week_monday()
    prospects = db.scalars(
        select(Prospect).where(Prospect.week == target_week)
    ).all()

    counts = {s.value: 0 for s in ProspectStatus}
    for p in prospects:
        counts[p.status.value] += 1

    return WeeklyStats(
        week=target_week,
        total=len(prospects),
        **counts,
    )


@router.get("/{prospect_id}", response_model=ProspectOut)
def get_prospect(prospect_id: int, db: Session = Depends(get_db)):
    prospect = db.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect não encontrado")
    return prospect


@router.patch("/{prospect_id}", response_model=ProspectOut)
def update_prospect(prospect_id: int, payload: ProspectUpdate, db: Session = Depends(get_db)):
    prospect = db.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect não encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prospect, field, value)
    db.commit()
    db.refresh(prospect)
    return prospect


@router.post("/{prospect_id}/contact", response_model=ProspectOut)
def mark_contacted(prospect_id: int, db: Session = Depends(get_db)):
    """Marca como contactado e registra a data de hoje."""
    prospect = db.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect não encontrado")
    if prospect.status == ProspectStatus.convertido:
        raise HTTPException(status_code=400, detail="Prospect já convertido em lead")
    prospect.status = ProspectStatus.contactado
    prospect.contacted_at = date.today()
    db.commit()
    db.refresh(prospect)
    return prospect


@router.post("/{prospect_id}/discard", response_model=ProspectOut)
def discard_prospect(prospect_id: int, reason: str = "", db: Session = Depends(get_db)):
    prospect = db.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect não encontrado")
    if prospect.status == ProspectStatus.convertido:
        raise HTTPException(status_code=400, detail="Prospect já convertido em lead")
    prospect.status = ProspectStatus.descartado
    prospect.discard_reason = reason
    db.commit()
    db.refresh(prospect)
    return prospect


@router.post("/{prospect_id}/convert", response_model=ProspectOut)
def convert_to_lead(prospect_id: int, payload: ConvertToLead, db: Session = Depends(get_db)):
    """Converte prospect em lead no CRM e atualiza status."""
    prospect = db.get(Prospect, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect não encontrado")
    if prospect.status == ProspectStatus.convertido:
        raise HTTPException(status_code=400, detail="Prospect já convertido")

    lead = Lead(
        company_name=prospect.company_name,
        contact_name=payload.contact_name,
        phone=payload.phone or prospect.phone,
        email=payload.email or prospect.email,
        source=_map_source(prospect.source.value),
        stage=Stage.qualificando,
        notes=payload.notes or prospect.notes,
    )
    db.add(lead)
    db.flush()

    prospect.status = ProspectStatus.convertido
    prospect.lead_id = lead.id
    db.commit()
    db.refresh(prospect)
    return prospect


def _map_source(prospect_source: str) -> Source:
    mapping = {
        "linkedin": Source.linkedin,
        "instagram": Source.instagram,
        "indicacao": Source.indicacao,
        "ex_colega": Source.indicacao,
        "google_maps": Source.prospeccao_ativa,
        "fornecedor": Source.outro,
        "associacao": Source.outro,
    }
    return mapping.get(prospect_source, Source.outro)
