"""Conversão prospect → lead: a integração entre os dois módulos."""

import pytest

from crm.models import Lead, Source, Stage
from prospecting.models import Prospect, ProspectSource, ProspectStatus
from prospecting.routers.prospects import _map_source

CONTATO = {"contact_name": "Rafael Pires"}


def test_converter_cria_o_lead_no_crm(client, make_prospect, db):
    prospect = make_prospect(company_name="Contabilidade Horizonte")

    r = client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    assert r.status_code == 200, r.text
    lead = db.query(Lead).one()
    assert lead.company_name == "Contabilidade Horizonte"
    assert lead.contact_name == "Rafael Pires"


def test_converter_marca_o_prospect_e_guarda_o_id_do_lead(client, make_prospect, db):
    prospect = make_prospect()

    body = client.post(f"/prospects/{prospect.id}/convert", json=CONTATO).json()

    assert body["status"] == "convertido"
    assert body["lead_id"] == db.query(Lead).one().id


def test_lead_convertido_entra_como_qualificando(client, make_prospect, db):
    prospect = make_prospect()

    client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    assert db.query(Lead).one().stage == Stage.qualificando


def test_converter_herda_telefone_e_email_do_prospect(client, make_prospect, db):
    prospect = make_prospect(phone="(27) 99666-1111", email="contato@horizonte.com.br")

    client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    lead = db.query(Lead).one()
    assert lead.phone == "(27) 99666-1111"
    assert lead.email == "contato@horizonte.com.br"


def test_payload_tem_prioridade_sobre_o_dado_do_prospect(client, make_prospect, db):
    prospect = make_prospect(phone="(27) 90000-0000", email="antigo@horizonte.com.br")

    client.post(
        f"/prospects/{prospect.id}/convert",
        json={**CONTATO, "phone": "(27) 91111-1111", "email": "novo@horizonte.com.br"},
    )

    lead = db.query(Lead).one()
    assert lead.phone == "(27) 91111-1111"
    assert lead.email == "novo@horizonte.com.br"


def test_converter_herda_as_notas_do_prospect_quando_o_payload_nao_traz(client, make_prospect, db):
    prospect = make_prospect(notes="Usa planilha para controlar entregas.")

    client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    assert db.query(Lead).one().notes == "Usa planilha para controlar entregas."


def test_converter_sem_nome_do_contato_devolve_422(client, make_prospect):
    prospect = make_prospect()

    assert client.post(f"/prospects/{prospect.id}/convert", json={}).status_code == 422


def test_converter_duas_vezes_devolve_400(client, make_prospect):
    prospect = make_prospect()
    client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    r = client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    assert r.status_code == 400
    assert r.json()["detail"] == "Prospect já convertido"


def test_converter_duas_vezes_nao_duplica_o_lead(client, make_prospect, db):
    prospect = make_prospect()
    client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)
    client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    assert db.query(Lead).count() == 1


def test_converter_prospect_inexistente_devolve_404(client):
    assert client.post("/prospects/9999/convert", json=CONTATO).status_code == 404


def test_converter_prospect_inexistente_nao_cria_lead(client, db):
    client.post("/prospects/9999/convert", json=CONTATO)

    assert db.query(Lead).count() == 0


def test_lead_convertido_aparece_no_resumo_do_pipeline(client, make_prospect):
    prospect = make_prospect()

    client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    assert client.get("/leads/pipeline/summary").json()["qualificando"] == 1


def test_conversao_conta_nas_metricas_da_semana(client, make_prospect):
    prospect = make_prospect()

    client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    body = client.get("/prospects/week/stats").json()
    assert body["convertido"] == 1
    assert body["pesquisando"] == 0


def test_o_lead_id_gravado_encontra_mesmo_o_lead(client, make_prospect):
    prospect = make_prospect()

    lead_id = client.post(f"/prospects/{prospect.id}/convert", json=CONTATO).json()["lead_id"]

    r = client.get(f"/leads/{lead_id}")
    assert r.status_code == 200
    assert r.json()["company_name"] == "Contabilidade Horizonte"


def test_descartar_depois_de_converter_nao_apaga_o_lead(client, make_prospect, db):
    """O endpoint de descarte não bloqueia convertidos — mas o lead no CRM não é tocado."""
    prospect = make_prospect()
    client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    client.post(f"/prospects/{prospect.id}/discard", params={"reason": "Enganei-me"})

    assert db.query(Lead).count() == 1
    db.expire_all()
    assert db.get(Prospect, prospect.id).lead_id is not None


@pytest.mark.parametrize(
    ("origem_prospect", "origem_lead"),
    [
        (ProspectSource.linkedin, Source.linkedin),
        (ProspectSource.instagram, Source.instagram),
        (ProspectSource.indicacao, Source.indicacao),
        (ProspectSource.ex_colega, Source.indicacao),
        (ProspectSource.google_maps, Source.prospeccao_ativa),
        (ProspectSource.fornecedor, Source.outro),
        (ProspectSource.associacao, Source.outro),
        (ProspectSource.outro, Source.outro),
    ],
)
def test_origem_do_prospect_vira_origem_do_lead(origem_prospect, origem_lead):
    assert _map_source(origem_prospect.value) == origem_lead


def test_origem_desconhecida_cai_no_default():
    assert _map_source("origem_que_nao_existe") == Source.outro


def test_toda_origem_de_prospect_sobrevive_a_conversao(client, make_prospect, db):
    """Nenhuma origem pode explodir na conversão — o default cobre o resto."""
    for origem in ProspectSource:
        prospect = make_prospect(company_name=f"Empresa {origem.value}", source=origem)
        r = client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)
        assert r.status_code == 200, origem.value

    assert db.query(Lead).count() == len(ProspectSource)


def test_prospect_contactado_pode_ser_convertido(client, make_prospect):
    prospect = make_prospect(status=ProspectStatus.contactado)

    r = client.post(f"/prospects/{prospect.id}/convert", json=CONTATO)

    assert r.status_code == 200
    assert r.json()["status"] == "convertido"
