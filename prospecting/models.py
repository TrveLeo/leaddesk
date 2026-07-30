import enum
from datetime import date, datetime

from sqlalchemy import (
    Date, DateTime, Enum, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from crm.database import Base


class ProspectStatus(str, enum.Enum):
    pesquisando = "pesquisando"
    qualificado = "qualificado"
    contactado = "contactado"
    convertido = "convertido"   # virou lead no CRM
    descartado = "descartado"


class ProspectSource(str, enum.Enum):
    google_maps = "google_maps"
    linkedin = "linkedin"
    instagram = "instagram"
    indicacao = "indicacao"
    ex_colega = "ex_colega"
    fornecedor = "fornecedor"
    associacao = "associacao"
    outro = "outro"


class Segment(str, enum.Enum):
    contabilidade = "contabilidade"
    marketing = "marketing"
    logistica = "logistica"
    imobiliaria = "imobiliaria"
    manutencao = "manutencao"
    ecommerce = "ecommerce"
    consultoria = "consultoria"
    servicos_tecnicos = "servicos_tecnicos"
    outro = "outro"


class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # identificação
    company_name: Mapped[str] = mapped_column(String(200))
    segment: Mapped[Segment] = mapped_column(Enum(Segment), default=Segment.outro)
    size_estimate: Mapped[str | None] = mapped_column(String(20))  # ex: "5-20", "20-50"
    source: Mapped[ProspectSource] = mapped_column(Enum(ProspectSource), default=ProspectSource.outro)

    # contato
    contact_name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(200))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))

    # qualificação
    signals: Mapped[str | None] = mapped_column(Text)   # sinais observados (texto livre)
    status: Mapped[ProspectStatus] = mapped_column(Enum(ProspectStatus), default=ProspectStatus.pesquisando)
    discard_reason: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

    # rastreamento
    week: Mapped[date | None] = mapped_column(Date)        # segunda-feira da semana de prospecção
    contacted_at: Mapped[date | None] = mapped_column(Date)
    lead_id: Mapped[int | None] = mapped_column(Integer)   # ID do lead criado no CRM após conversão
