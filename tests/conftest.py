import os
import tempfile
from collections.abc import Generator
from datetime import date, timedelta

import pytest

# Precisa vir antes de importar qualquer módulo que crie o engine.
_TMP = tempfile.mkdtemp(prefix="leaddesk-test-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP}/test.db")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from crm.database import Base, SessionLocal, engine  # noqa: E402
from crm.models import Lead, Source, Stage  # noqa: E402
from main import app  # noqa: E402
from prospecting.models import Prospect, ProspectSource, ProspectStatus, Segment  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Cliente sem lifespan — o agendador não sobe durante os testes."""
    yield TestClient(app)


@pytest.fixture
def today() -> date:
    return date.today()


@pytest.fixture
def monday(today: date) -> date:
    """Segunda-feira da semana corrente — é assim que o módulo agrupa prospects."""
    return today - timedelta(days=today.weekday())


@pytest.fixture
def make_lead(db: Session):
    """Cria um lead direto no banco, sem passar pela API."""

    def _make(**overrides) -> Lead:
        data = {
            "company_name": "Padaria Trigo Dourado",
            "contact_name": "Marina Alves",
            "phone": "(27) 99999-0001",
            "email": "contato@trigodourado.com.br",
            "source": Source.prospeccao_ativa,
            "stage": Stage.novo_contato,
        }
        data.update(overrides)
        lead = Lead(**data)
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    return _make


@pytest.fixture
def make_prospect(db: Session, monday: date):
    """Cria um prospect direto no banco, sem passar pela API."""

    def _make(**overrides) -> Prospect:
        data = {
            "company_name": "Contabilidade Horizonte",
            "segment": Segment.contabilidade,
            "source": ProspectSource.google_maps,
            "status": ProspectStatus.pesquisando,
            "week": monday,
        }
        data.update(overrides)
        prospect = Prospect(**data)
        db.add(prospect)
        db.commit()
        db.refresh(prospect)
        return prospect

    return _make
