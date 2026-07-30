"""Leads: CRUD, filtro por etapa e ordenação da lista de trabalho."""

from datetime import date, timedelta

from crm.models import Lead, Source, Stage

PAYLOAD = {
    "company_name": "Transportadora Rota Certa",
    "contact_name": "Diego Moraes",
    "phone": "(27) 99888-1234",
    "email": "diego@rotacerta.com.br",
    "source": "indicacao",
    "stage": "qualificando",
    "notes": "Indicado pelo contador.",
    "next_action": "Enviar proposta",
    "next_action_date": "2026-08-10",
}


def test_criar_lead_devolve_201_e_o_recurso(client):
    r = client.post("/leads/", json=PAYLOAD)
    assert r.status_code == 201, r.text

    body = r.json()
    assert body["id"] > 0
    assert body["company_name"] == "Transportadora Rota Certa"
    assert body["source"] == "indicacao"
    assert body["stage"] == "qualificando"
    assert body["interactions"] == []


def test_criar_lead_preenche_created_at_e_updated_at(client):
    body = client.post("/leads/", json=PAYLOAD).json()

    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_criar_lead_usa_os_defaults_quando_o_payload_e_minimo(client):
    r = client.post(
        "/leads/", json={"company_name": "Ateliê Linha Fina", "contact_name": "Bruna Sato"}
    )

    body = r.json()
    assert body["stage"] == "novo_contato"
    assert body["source"] == "outro"
    assert body["phone"] is None
    assert body["next_action_date"] is None


def test_criar_lead_sem_campo_obrigatorio_devolve_422(client):
    r = client.post("/leads/", json={"company_name": "Só a empresa"})

    assert r.status_code == 422


def test_criar_lead_com_etapa_inexistente_devolve_422(client):
    r = client.post("/leads/", json={**PAYLOAD, "stage": "etapa_que_nao_existe"})

    assert r.status_code == 422


def test_listar_leads_vazio_devolve_lista_vazia(client):
    r = client.get("/leads/")

    assert r.status_code == 200
    assert r.json() == []


def test_listar_leads_traz_o_resumo_e_nao_o_lead_inteiro(client, make_lead):
    make_lead(next_action="Ligar de volta")

    item = client.get("/leads/").json()[0]

    assert set(item) == {
        "id",
        "company_name",
        "contact_name",
        "stage",
        "source",
        "next_action",
        "next_action_date",
        "interaction_count",
    }


def test_listar_leads_filtra_por_etapa(client, make_lead):
    make_lead(company_name="Em negociação", stage=Stage.negociacao)
    make_lead(company_name="Já é cliente", stage=Stage.cliente)

    r = client.get("/leads/", params={"stage": "negociacao"})

    nomes = [lead["company_name"] for lead in r.json()]
    assert nomes == ["Em negociação"]


def test_listar_leads_com_etapa_invalida_devolve_422(client):
    r = client.get("/leads/", params={"stage": "inexistente"})

    assert r.status_code == 422


def test_listar_leads_ordena_por_proxima_acao_mais_urgente(client, make_lead, today):
    make_lead(company_name="Semana que vem", next_action_date=today + timedelta(days=7))
    make_lead(company_name="Atrasado", next_action_date=today - timedelta(days=3))
    make_lead(company_name="Hoje", next_action_date=today)

    nomes = [lead["company_name"] for lead in client.get("/leads/").json()]

    assert nomes == ["Atrasado", "Hoje", "Semana que vem"]


def test_listar_leads_joga_sem_data_para_o_fim(client, make_lead, today):
    make_lead(company_name="Sem data", next_action_date=None)
    make_lead(company_name="Com data", next_action_date=today + timedelta(days=30))

    nomes = [lead["company_name"] for lead in client.get("/leads/").json()]

    assert nomes == ["Com data", "Sem data"]


def test_listar_leads_conta_as_interacoes_de_cada_um(client, make_lead, today):
    lead = make_lead()
    for _ in range(3):
        client.post(
            f"/leads/{lead.id}/interactions/",
            json={"description": "Contato", "date": today.isoformat()},
        )

    assert client.get("/leads/").json()[0]["interaction_count"] == 3


def test_buscar_lead_traz_as_interacoes_aninhadas(client, make_lead, today):
    lead = make_lead()
    client.post(
        f"/leads/{lead.id}/interactions/",
        json={"type": "reuniao", "description": "Call de diagnóstico", "date": today.isoformat()},
    )

    body = client.get(f"/leads/{lead.id}").json()

    assert len(body["interactions"]) == 1
    assert body["interactions"][0]["description"] == "Call de diagnóstico"


def test_buscar_lead_inexistente_devolve_404(client):
    r = client.get("/leads/9999")

    assert r.status_code == 404
    assert r.json()["detail"] == "Lead não encontrado"


def test_atualizar_lead_muda_so_o_campo_enviado(client, make_lead):
    lead = make_lead(notes="Anotação original")

    body = client.patch(f"/leads/{lead.id}", json={"stage": "proposta_enviada"}).json()

    assert body["stage"] == "proposta_enviada"
    assert body["notes"] == "Anotação original"
    assert body["company_name"] == "Padaria Trigo Dourado"


def test_atualizar_lead_aceita_limpar_campo_opcional(client, make_lead):
    lead = make_lead(next_action="Ligar", next_action_date=date(2026, 8, 1))

    body = client.patch(f"/leads/{lead.id}", json={"next_action_date": None}).json()

    assert body["next_action_date"] is None
    assert body["next_action"] == "Ligar"


def test_atualizar_lead_com_corpo_vazio_nao_quebra(client, make_lead):
    lead = make_lead()

    r = client.patch(f"/leads/{lead.id}", json={})

    assert r.status_code == 200
    assert r.json()["stage"] == "novo_contato"


def test_atualizar_lead_persiste_no_banco(client, make_lead, db):
    lead = make_lead()

    client.patch(f"/leads/{lead.id}", json={"contact_name": "Outro Contato"})

    db.expire_all()
    assert db.get(Lead, lead.id).contact_name == "Outro Contato"


def test_atualizar_lead_inexistente_devolve_404(client):
    r = client.patch("/leads/9999", json={"stage": "cliente"})

    assert r.status_code == 404


def test_apagar_lead_devolve_204_e_some_da_listagem(client, make_lead):
    lead = make_lead()

    assert client.delete(f"/leads/{lead.id}").status_code == 204
    assert client.get(f"/leads/{lead.id}").status_code == 404
    assert client.get("/leads/").json() == []


def test_apagar_lead_leva_junto_as_interacoes(client, make_lead, db, today):
    from crm.models import Interaction

    lead = make_lead()
    client.post(
        f"/leads/{lead.id}/interactions/",
        json={"description": "Primeiro contato", "date": today.isoformat()},
    )

    client.delete(f"/leads/{lead.id}")

    db.expire_all()
    assert db.query(Interaction).count() == 0


def test_apagar_lead_inexistente_devolve_404(client):
    r = client.delete("/leads/9999")

    assert r.status_code == 404


def test_resumo_do_pipeline_lista_as_oito_etapas_mesmo_zeradas(client):
    resumo = client.get("/leads/pipeline/summary").json()

    assert len(resumo) == 8
    assert set(resumo) == {stage.value for stage in Stage}
    assert set(resumo.values()) == {0}


def test_resumo_do_pipeline_conta_por_etapa(client, make_lead):
    make_lead(stage=Stage.novo_contato)
    make_lead(stage=Stage.negociacao)
    make_lead(stage=Stage.negociacao)
    make_lead(stage=Stage.cliente)

    resumo = client.get("/leads/pipeline/summary").json()

    assert resumo["novo_contato"] == 1
    assert resumo["negociacao"] == 2
    assert resumo["cliente"] == 1
    assert resumo["sem_momento"] == 0


def test_resumo_do_pipeline_acompanha_a_mudanca_de_etapa(client, make_lead):
    lead = make_lead(stage=Stage.qualificando)

    client.patch(f"/leads/{lead.id}", json={"stage": "cliente"})

    resumo = client.get("/leads/pipeline/summary").json()
    assert resumo["qualificando"] == 0
    assert resumo["cliente"] == 1


def test_todas_as_origens_sao_aceitas_na_criacao(client):
    for source in Source:
        r = client.post(
            "/leads/",
            json={
                "company_name": f"Empresa {source.value}",
                "contact_name": "Contato",
                "source": source.value,
            },
        )
        assert r.status_code == 201, source.value
        assert r.json()["source"] == source.value


def test_todas_as_etapas_sao_aceitas_na_criacao(client):
    for stage in Stage:
        r = client.post(
            "/leads/",
            json={
                "company_name": f"Empresa {stage.value}",
                "contact_name": "Contato",
                "stage": stage.value,
            },
        )
        assert r.status_code == 201, stage.value
        assert r.json()["stage"] == stage.value
