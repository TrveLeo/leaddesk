"""Prospects: cadastro, filtros, transições de status e métricas da semana."""

from datetime import date, timedelta

from prospecting.models import Prospect, ProspectSource, ProspectStatus, Segment

PAYLOAD = {
    "company_name": "Imobiliária Vista Mar",
    "segment": "imobiliaria",
    "size_estimate": "20-50",
    "source": "google_maps",
    "contact_name": "Rafael Pires",
    "phone": "(27) 99777-4321",
    "signals": "Site sem integração com o CRM; planilha manual de visitas.",
}


def test_criar_prospect_devolve_201(client):
    r = client.post("/prospects/", json=PAYLOAD)

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["company_name"] == "Imobiliária Vista Mar"
    assert body["segment"] == "imobiliaria"
    assert body["status"] == "pesquisando"
    assert body["lead_id"] is None


def test_criar_prospect_sem_semana_assume_a_segunda_da_semana_corrente(client, monday):
    body = client.post("/prospects/", json=PAYLOAD).json()

    assert body["week"] == monday.isoformat()


def test_criar_prospect_respeita_a_semana_informada(client):
    body = client.post("/prospects/", json={**PAYLOAD, "week": "2026-06-01"}).json()

    assert body["week"] == "2026-06-01"


def test_criar_prospect_usa_os_defaults_quando_o_payload_e_minimo(client):
    body = client.post("/prospects/", json={"company_name": "Só o nome"}).json()

    assert body["segment"] == "outro"
    assert body["source"] == "outro"
    assert body["status"] == "pesquisando"
    assert body["contact_name"] is None


def test_criar_prospect_sem_nome_devolve_422(client):
    r = client.post("/prospects/", json={"segment": "logistica"})

    assert r.status_code == 422


def test_criar_prospect_com_segmento_invalido_devolve_422(client):
    r = client.post("/prospects/", json={**PAYLOAD, "segment": "mineracao_espacial"})

    assert r.status_code == 422


def test_todos_os_segmentos_sao_aceitos(client):
    for segment in Segment:
        r = client.post(
            "/prospects/", json={"company_name": f"Empresa {segment.value}", "segment": segment.value}
        )
        assert r.status_code == 201, segment.value


def test_todas_as_origens_de_prospect_sao_aceitas(client):
    for source in ProspectSource:
        r = client.post(
            "/prospects/", json={"company_name": f"Empresa {source.value}", "source": source.value}
        )
        assert r.status_code == 201, source.value


def test_listar_prospects_vazio_devolve_lista_vazia(client):
    assert client.get("/prospects/").json() == []


def test_listar_prospects_filtra_por_status(client, make_prospect):
    make_prospect(company_name="Ainda pesquisando", status=ProspectStatus.pesquisando)
    make_prospect(company_name="Já contactado", status=ProspectStatus.contactado)

    r = client.get("/prospects/", params={"status": "contactado"})

    assert [p["company_name"] for p in r.json()] == ["Já contactado"]


def test_listar_prospects_filtra_por_semana(client, make_prospect, monday):
    make_prospect(company_name="Desta semana", week=monday)
    make_prospect(company_name="Da semana passada", week=monday - timedelta(days=7))

    r = client.get("/prospects/", params={"week": monday.isoformat()})

    assert [p["company_name"] for p in r.json()] == ["Desta semana"]


def test_listar_prospects_combina_status_e_semana(client, make_prospect, monday):
    outra_semana = monday - timedelta(days=7)
    make_prospect(company_name="Alvo", status=ProspectStatus.qualificado, week=monday)
    make_prospect(company_name="Status errado", status=ProspectStatus.descartado, week=monday)
    make_prospect(company_name="Semana errada", status=ProspectStatus.qualificado, week=outra_semana)

    r = client.get("/prospects/", params={"status": "qualificado", "week": monday.isoformat()})

    assert [p["company_name"] for p in r.json()] == ["Alvo"]


def test_listar_prospects_com_status_invalido_devolve_422(client):
    assert client.get("/prospects/", params={"status": "talvez"}).status_code == 422


def test_buscar_prospect_traz_o_registro_completo(client, make_prospect):
    prospect = make_prospect(signals="Planilha manual de visitas.", size_estimate="20-50")

    body = client.get(f"/prospects/{prospect.id}").json()

    assert body["id"] == prospect.id
    assert body["company_name"] == "Contabilidade Horizonte"
    assert body["signals"] == "Planilha manual de visitas."
    assert body["size_estimate"] == "20-50"
    assert body["status"] == "pesquisando"


def test_buscar_prospect_inexistente_devolve_404(client):
    r = client.get("/prospects/9999")

    assert r.status_code == 404
    assert r.json()["detail"] == "Prospect não encontrado"


def test_atualizar_prospect_muda_so_o_campo_enviado(client, make_prospect):
    prospect = make_prospect(notes="Nota original")

    body = client.patch(f"/prospects/{prospect.id}", json={"status": "qualificado"}).json()

    assert body["status"] == "qualificado"
    assert body["notes"] == "Nota original"


def test_atualizar_prospect_persiste_no_banco(client, make_prospect, db):
    prospect = make_prospect()

    client.patch(f"/prospects/{prospect.id}", json={"email": "novo@empresa.com.br"})

    db.expire_all()
    assert db.get(Prospect, prospect.id).email == "novo@empresa.com.br"


def test_atualizar_prospect_inexistente_devolve_404(client):
    assert client.patch("/prospects/9999", json={"status": "qualificado"}).status_code == 404


def test_marcar_contactado_muda_status_e_grava_a_data(client, make_prospect, today):
    prospect = make_prospect()

    body = client.post(f"/prospects/{prospect.id}/contact").json()

    assert body["status"] == "contactado"
    assert body["contacted_at"] == today.isoformat()


def test_marcar_contactado_em_prospect_ja_convertido_devolve_400(client, make_prospect):
    prospect = make_prospect(status=ProspectStatus.convertido)

    r = client.post(f"/prospects/{prospect.id}/contact")

    assert r.status_code == 400
    assert r.json()["detail"] == "Prospect já convertido em lead"


def test_marcar_contactado_em_prospect_inexistente_devolve_404(client):
    assert client.post("/prospects/9999/contact").status_code == 404


def test_descartar_prospect_grava_o_motivo(client, make_prospect):
    prospect = make_prospect()

    body = client.post(
        f"/prospects/{prospect.id}/discard", params={"reason": "Sem orçamento este ano"}
    ).json()

    assert body["status"] == "descartado"
    assert body["discard_reason"] == "Sem orçamento este ano"


def test_descartar_prospect_sem_motivo_deixa_o_campo_vazio(client, make_prospect):
    prospect = make_prospect()

    body = client.post(f"/prospects/{prospect.id}/discard").json()

    assert body["status"] == "descartado"
    assert body["discard_reason"] == ""


def test_descartar_prospect_inexistente_devolve_404(client):
    assert client.post("/prospects/9999/discard").status_code == 404


def test_descartar_prospect_ja_convertido_devolve_400(client, make_prospect):
    prospect = make_prospect(status=ProspectStatus.convertido)

    r = client.post(f"/prospects/{prospect.id}/discard", params={"reason": "tarde demais"})

    assert r.status_code == 400
    assert r.json()["detail"] == "Prospect já convertido em lead"


def test_descartar_e_contactar_recusam_convertido_com_a_mesma_resposta(client, make_prospect):
    """As duas transições tratam `convertido` como estado final, do mesmo jeito."""
    prospect = make_prospect(status=ProspectStatus.convertido)

    descarte = client.post(f"/prospects/{prospect.id}/discard")
    contato = client.post(f"/prospects/{prospect.id}/contact")

    assert descarte.status_code == contato.status_code == 400
    assert descarte.json()["detail"] == contato.json()["detail"]


def test_prospect_descartado_ainda_pode_ser_descartado_de_novo(client, make_prospect):
    """Só `convertido` é terminal — redescartar com outro motivo é corrigir registro."""
    prospect = make_prospect(status=ProspectStatus.descartado, discard_reason="motivo antigo")

    r = client.post(f"/prospects/{prospect.id}/discard", params={"reason": "motivo correto"})

    assert r.status_code == 200
    assert r.json()["discard_reason"] == "motivo correto"


def test_metricas_da_semana_sem_prospects_vem_zeradas(client, monday):
    body = client.get("/prospects/week/stats").json()

    assert body["week"] == monday.isoformat()
    assert body["total"] == 0
    assert body["pesquisando"] == 0
    assert body["convertido"] == 0


def test_metricas_da_semana_contam_por_status(client, make_prospect):
    make_prospect(status=ProspectStatus.pesquisando)
    make_prospect(status=ProspectStatus.qualificado)
    make_prospect(status=ProspectStatus.qualificado)
    make_prospect(status=ProspectStatus.contactado)
    make_prospect(status=ProspectStatus.descartado)

    body = client.get("/prospects/week/stats").json()

    assert body["total"] == 5
    assert body["pesquisando"] == 1
    assert body["qualificado"] == 2
    assert body["contactado"] == 1
    assert body["descartado"] == 1
    assert body["convertido"] == 0


def test_metricas_da_semana_ignoram_outras_semanas(client, make_prospect, monday):
    make_prospect(week=monday)
    make_prospect(week=monday - timedelta(days=7))

    assert client.get("/prospects/week/stats").json()["total"] == 1


def test_metricas_aceitam_uma_semana_explicita(client, make_prospect, monday):
    semana_passada = monday - timedelta(days=7)
    make_prospect(week=semana_passada)
    make_prospect(week=semana_passada)
    make_prospect(week=monday)

    body = client.get("/prospects/week/stats", params={"week": semana_passada.isoformat()}).json()

    assert body["week"] == semana_passada.isoformat()
    assert body["total"] == 2


def test_metricas_trazem_as_metas_do_plano(client):
    body = client.get("/prospects/week/stats").json()

    assert body["meta_pesquisadas"] == 20
    assert body["meta_contactadas"] == 10


def test_metricas_de_semana_sem_dado_devolvem_zero_e_nao_404(client, make_prospect, monday):
    make_prospect(week=monday)

    body = client.get("/prospects/week/stats", params={"week": "2026-01-05"}).json()

    assert body["total"] == 0
    assert body["week"] == "2026-01-05"


def test_a_rota_de_metricas_nao_e_confundida_com_um_id(client, make_prospect):
    """`/prospects/week/stats` precisa ganhar de `/prospects/{prospect_id}`."""
    make_prospect()

    r = client.get("/prospects/week/stats")

    assert r.status_code == 200
    assert "meta_pesquisadas" in r.json()


def test_semana_e_sempre_uma_segunda_feira(client, monday):
    client.post("/prospects/", json=PAYLOAD)

    week = date.fromisoformat(client.get("/prospects/").json()[0]["week"])

    assert week.weekday() == 0
