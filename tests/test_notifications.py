"""Notificação por Telegram: degradação silenciosa quando não há credencial."""

import httpx
import pytest

from crm import notifications


@pytest.fixture
def com_credencial(monkeypatch):
    monkeypatch.setattr(notifications.settings, "telegram_bot_token", "token-de-teste")
    monkeypatch.setattr(notifications.settings, "telegram_chat_id", "12345")


@pytest.fixture
def sem_credencial(monkeypatch):
    monkeypatch.setattr(notifications.settings, "telegram_bot_token", "")
    monkeypatch.setattr(notifications.settings, "telegram_chat_id", "")


def test_sem_token_devolve_false_e_nao_chama_a_rede(sem_credencial, monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("não deveria chamar a rede sem credencial")

    monkeypatch.setattr(notifications.httpx, "post", explode)

    assert notifications.send_telegram("olá") is False


def test_sem_chat_id_devolve_false(monkeypatch):
    monkeypatch.setattr(notifications.settings, "telegram_bot_token", "token-de-teste")
    monkeypatch.setattr(notifications.settings, "telegram_chat_id", "")

    assert notifications.send_telegram("olá") is False


def test_envio_bem_sucedido_devolve_true(com_credencial, monkeypatch):
    chamadas = []

    def fake_post(url, json, timeout):
        chamadas.append((url, json))
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(notifications.httpx, "post", fake_post)

    assert notifications.send_telegram("mensagem") is True
    url, payload = chamadas[0]
    assert "token-de-teste" in url
    assert payload["chat_id"] == "12345"
    assert payload["text"] == "mensagem"
    assert payload["parse_mode"] == "Markdown"


def test_erro_http_devolve_false_em_vez_de_propagar(com_credencial, monkeypatch):
    def fake_post(url, json, timeout):
        return httpx.Response(500, request=httpx.Request("POST", url))

    monkeypatch.setattr(notifications.httpx, "post", fake_post)

    assert notifications.send_telegram("mensagem") is False


def test_falha_de_rede_devolve_false_em_vez_de_propagar(com_credencial, monkeypatch):
    def fake_post(url, json, timeout):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(notifications.httpx, "post", fake_post)

    assert notifications.send_telegram("mensagem") is False


def test_o_job_nao_quebra_quando_a_notificacao_falha(com_credencial, monkeypatch, make_lead, today):
    """O follow-up é informativo — falha de envio não pode derrubar o agendador."""
    from crm import jobs

    monkeypatch.setattr(
        notifications.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("x"))
    )
    make_lead(next_action_date=today)

    jobs.followup_job()  # não levanta
