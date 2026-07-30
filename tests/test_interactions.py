"""Interações: histórico de contato pendurado no lead."""

from datetime import timedelta

from crm.models import InteractionType


def test_registrar_interacao_devolve_201(client, make_lead, today):
    lead = make_lead()

    r = client.post(
        f"/leads/{lead.id}/interactions/",
        json={"type": "ligacao", "description": "Falei com a Marina", "date": today.isoformat()},
    )

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["lead_id"] == lead.id
    assert body["type"] == "ligacao"
    assert body["description"] == "Falei com a Marina"


def test_registrar_interacao_usa_mensagem_como_tipo_padrao(client, make_lead, today):
    lead = make_lead()

    r = client.post(
        f"/leads/{lead.id}/interactions/",
        json={"description": "WhatsApp enviado", "date": today.isoformat()},
    )

    assert r.json()["type"] == "mensagem"


def test_registrar_interacao_sem_data_devolve_422(client, make_lead):
    lead = make_lead()

    r = client.post(f"/leads/{lead.id}/interactions/", json={"description": "Sem data"})

    assert r.status_code == 422


def test_registrar_interacao_com_tipo_invalido_devolve_422(client, make_lead, today):
    lead = make_lead()

    r = client.post(
        f"/leads/{lead.id}/interactions/",
        json={"type": "telepatia", "description": "x", "date": today.isoformat()},
    )

    assert r.status_code == 422


def test_registrar_interacao_em_lead_inexistente_devolve_404(client, today):
    r = client.post(
        "/leads/9999/interactions/",
        json={"description": "Órfã", "date": today.isoformat()},
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Lead não encontrado"


def test_todos_os_tipos_de_interacao_sao_aceitos(client, make_lead, today):
    lead = make_lead()

    for tipo in InteractionType:
        r = client.post(
            f"/leads/{lead.id}/interactions/",
            json={"type": tipo.value, "description": tipo.value, "date": today.isoformat()},
        )
        assert r.status_code == 201, tipo.value


def test_listar_interacoes_de_lead_sem_historico_devolve_vazio(client, make_lead):
    lead = make_lead()

    r = client.get(f"/leads/{lead.id}/interactions/")

    assert r.status_code == 200
    assert r.json() == []


def test_listar_interacoes_ordena_da_mais_recente_para_a_mais_antiga(client, make_lead, today):
    lead = make_lead()
    for dias, texto in [(10, "Antiga"), (1, "Recente"), (5, "Meio")]:
        client.post(
            f"/leads/{lead.id}/interactions/",
            json={"description": texto, "date": (today - timedelta(days=dias)).isoformat()},
        )

    textos = [i["description"] for i in client.get(f"/leads/{lead.id}/interactions/").json()]

    assert textos == ["Recente", "Meio", "Antiga"]


def test_listar_interacoes_de_lead_inexistente_devolve_404(client):
    r = client.get("/leads/9999/interactions/")

    assert r.status_code == 404


def test_listar_interacoes_nao_vaza_historico_de_outro_lead(client, make_lead, today):
    lead_a = make_lead(company_name="Empresa A")
    lead_b = make_lead(company_name="Empresa B")
    client.post(
        f"/leads/{lead_a.id}/interactions/",
        json={"description": "Só da A", "date": today.isoformat()},
    )

    assert client.get(f"/leads/{lead_b.id}/interactions/").json() == []


def test_apagar_interacao_devolve_204(client, make_lead, today):
    lead = make_lead()
    interacao = client.post(
        f"/leads/{lead.id}/interactions/",
        json={"description": "Errada", "date": today.isoformat()},
    ).json()

    r = client.delete(f"/leads/{lead.id}/interactions/{interacao['id']}")

    assert r.status_code == 204
    assert client.get(f"/leads/{lead.id}/interactions/").json() == []


def test_apagar_interacao_inexistente_devolve_404(client, make_lead):
    lead = make_lead()

    r = client.delete(f"/leads/{lead.id}/interactions/9999")

    assert r.status_code == 404
    assert r.json()["detail"] == "Interação não encontrada"


def test_apagar_interacao_pelo_lead_errado_devolve_404(client, make_lead, today):
    lead_a = make_lead(company_name="Empresa A")
    lead_b = make_lead(company_name="Empresa B")
    interacao = client.post(
        f"/leads/{lead_a.id}/interactions/",
        json={"description": "Da A", "date": today.isoformat()},
    ).json()

    r = client.delete(f"/leads/{lead_b.id}/interactions/{interacao['id']}")

    assert r.status_code == 404
    assert len(client.get(f"/leads/{lead_a.id}/interactions/").json()) == 1
