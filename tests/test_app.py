"""Montagem da aplicação: rotas registradas, health e ciclo do agendador."""

from fastapi.testclient import TestClient

from crm import scheduler
from main import app


def test_health_responde_ok(client):
    r = client.get("/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_os_dois_modulos_estao_montados_na_mesma_app():
    rotas = {rota.path for rota in app.routes}

    assert "/leads/" in rotas
    assert "/leads/{lead_id}/interactions/" in rotas
    assert "/prospects/" in rotas


def _rotas_publicas() -> set[tuple[str, str]]:
    return {
        (rota.path, metodo)
        for rota in app.routes
        if hasattr(rota, "methods")
        for metodo in rota.methods
        if metodo != "HEAD" and not rota.path.startswith(("/openapi", "/docs", "/redoc"))
    }


def test_a_app_expoe_dezessete_endpoints_de_negocio():
    """Este número vai para o README do case — se mudar, o texto muda junto."""
    infra = {("/health", "GET"), ("/jobs/followup", "POST")}

    assert len(_rotas_publicas() - infra) == 17


def test_cada_endpoint_de_negocio_pertence_a_um_dos_dois_modulos():
    infra = {("/health", "GET"), ("/jobs/followup", "POST")}

    negocio = _rotas_publicas() - infra
    leads = {r for r in negocio if r[0].startswith("/leads")}
    prospects = {r for r in negocio if r[0].startswith("/prospects")}

    assert len(leads) == 9      # 6 de lead + 3 de interação
    assert len(prospects) == 8
    assert leads | prospects == negocio


def test_o_schema_openapi_e_gerado_sem_erro(client):
    r = client.get("/openapi.json")

    assert r.status_code == 200
    assert r.json()["info"]["title"] == "LeadDesk"


def test_o_agendador_sobe_e_desce_com_a_aplicacao(monkeypatch):
    eventos = []
    monkeypatch.setattr(scheduler._scheduler, "add_job", lambda *a, **k: eventos.append("add"))
    monkeypatch.setattr(scheduler._scheduler, "start", lambda *a, **k: eventos.append("start"))
    monkeypatch.setattr(scheduler._scheduler, "shutdown", lambda *a, **k: eventos.append("stop"))

    with TestClient(app):
        assert eventos == ["add", "start"]

    assert eventos == ["add", "start", "stop"]


def test_o_job_e_agendado_no_horario_configurado(monkeypatch):
    from crm.config import settings

    capturado = {}
    monkeypatch.setattr(
        scheduler._scheduler, "add_job", lambda fn, **kw: capturado.update(kw, fn=fn)
    )
    monkeypatch.setattr(scheduler._scheduler, "start", lambda: None)

    scheduler.start()

    assert capturado["trigger"] == "cron"
    assert capturado["hour"] == settings.followup_job_hour
    assert capturado["minute"] == settings.followup_job_minute
    assert capturado["id"] == "followup"
    assert capturado["replace_existing"] is True
