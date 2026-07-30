import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm.database import Base


class Stage(str, enum.Enum):
    novo_contato = "novo_contato"
    qualificando = "qualificando"
    reuniao_agendada = "reuniao_agendada"
    proposta_enviada = "proposta_enviada"
    negociacao = "negociacao"
    cliente = "cliente"
    acompanhamento = "acompanhamento"
    sem_momento = "sem_momento"


class Source(str, enum.Enum):
    linkedin = "linkedin"
    instagram = "instagram"
    whatsapp = "whatsapp"
    indicacao = "indicacao"
    prospeccao_ativa = "prospeccao_ativa"
    plataforma = "plataforma"
    outro = "outro"


class InteractionType(str, enum.Enum):
    mensagem = "mensagem"
    ligacao = "ligacao"
    reuniao = "reuniao"
    proposta = "proposta"
    follow_up = "follow_up"
    outro = "outro"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    company_name: Mapped[str] = mapped_column(String(200))
    contact_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(200))

    source: Mapped[Source] = mapped_column(Enum(Source), default=Source.outro)
    stage: Mapped[Stage] = mapped_column(Enum(Stage), default=Stage.novo_contato)

    notes: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(String(500))
    next_action_date: Mapped[date | None] = mapped_column(Date)

    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="Interaction.created_at"
    )


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    type: Mapped[InteractionType] = mapped_column(Enum(InteractionType), default=InteractionType.mensagem)
    description: Mapped[str] = mapped_column(Text)
    date: Mapped[date] = mapped_column(Date)

    lead: Mapped["Lead"] = relationship(back_populates="interactions")
