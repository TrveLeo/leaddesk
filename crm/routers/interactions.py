from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from crm.database import get_db
from crm.models import Interaction, Lead
from crm.schemas import InteractionCreate, InteractionOut

router = APIRouter(prefix="/leads/{lead_id}/interactions", tags=["interactions"])


@router.post("/", response_model=InteractionOut, status_code=201)
def add_interaction(lead_id: int, payload: InteractionCreate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    interaction = Interaction(lead_id=lead_id, **payload.model_dump())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


@router.get("/", response_model=list[InteractionOut])
def list_interactions(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return db.scalars(
        select(Interaction).where(Interaction.lead_id == lead_id).order_by(Interaction.date.desc())
    ).all()


@router.delete("/{interaction_id}", status_code=204)
def delete_interaction(lead_id: int, interaction_id: int, db: Session = Depends(get_db)):
    interaction = db.scalar(
        select(Interaction).where(Interaction.id == interaction_id, Interaction.lead_id == lead_id)
    )
    if not interaction:
        raise HTTPException(status_code=404, detail="Interação não encontrada")
    db.delete(interaction)
    db.commit()
