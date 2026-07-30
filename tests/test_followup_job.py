"""Job de follow-up: seleção dos leads e formato da mensagem.

O envio ao Telegram é substituído por um espião — os testes não tocam a rede.
"""

from datetime import timedelta

import pytest

from crm import jobs
from crm.models import Stage


@pytest.fixture
def enviadas(monkeypatch) -> list[str]:
    """Captura as mensagens que iriam para o Telegram."""
    capturadas: list[str] = []
    monkeypatch.setattr(jobs, "send_telegram", lambda msg: capturadas.append(msg) or True)
    return capturadas


def test_sem_lead_nenhum_nao_envia_nada(enviadas):
    jobs.followup_job()

    assert enviadas == []


def test_lead_sem_data_de_proxima_acao_nao_entra(enviadas, make_lead):
    make_lead(next_action_date=None, next_action="Ligar um dia desses")

    jobs.followup_job()

    assert enviadas == []


def test_lead_com_acao_para_hoje_entra(enviadas, make_lead, today):
    make_lead(next_action_date=today, next_action="Enviar proposta")

    jobs.followup_job()

    assert len(enviadas) == 1
    assert "Padaria Trigo Dourado" in enviadas[0]
    assert "Enviar proposta" in enviadas[0]


def test_lead_atrasado_entra_com_a_contagem_de_dias(enviadas, make_lead, today):
    make_lead(next_action_date=today - timedelta(days=3))

    jobs.followup_job()

    assert "Atrasados" in enviadas[0]
    assert "3d atraso" in enviadas[0]


def test_lead_dentro_da_janela_de_antecedencia_entra(enviadas, make_lead, today):
    """O default é `followup_days_ahead=1` — amanhã conta, depois de amanhã não."""
    make_lead(company_name="É amanhã", next_action_date=today + timedelta(days=1))

    jobs.followup_job()

    assert "É amanhã" in enviadas[0]


def test_lead_fora_da_janela_de_antecedencia_fica_de_fora(enviadas, make_lead, today):
    make_lead(company_name="Semana que vem", next_action_date=today + timedelta(days=7))

    jobs.followup_job()

    assert enviadas == []


def test_lead_ja_cliente_e_ignorado(enviadas, make_lead, today):
    make_lead(stage=Stage.cliente, next_action_date=today)

    jobs.followup_job()

    assert enviadas == []


def test_lead_sem_momento_e_ignorado(enviadas, make_lead, today):
    make_lead(stage=Stage.sem_momento, next_action_date=today)

    jobs.followup_job()

    assert enviadas == []


def test_as_demais_etapas_entram_normalmente(enviadas, make_lead, today):
    ativas = [s for s in Stage if s not in {Stage.cliente, Stage.sem_momento}]
    for stage in ativas:
        make_lead(company_name=f"Empresa {stage.value}", stage=stage, next_action_date=today)

    jobs.followup_job()

    for stage in ativas:
        assert f"Empresa {stage.value}" in enviadas[0], stage.value


def test_a_mensagem_separa_atrasados_hoje_e_proximos(enviadas, make_lead, today):
    make_lead(company_name="Atrasado", next_action_date=today - timedelta(days=2))
    make_lead(company_name="De hoje", next_action_date=today)
    make_lead(company_name="De amanhã", next_action_date=today + timedelta(days=1))

    jobs.followup_job()

    msg = enviadas[0]
    assert "Atrasados" in msg and "Para hoje" in msg and "Próximos" in msg
    assert msg.index("Atrasados") < msg.index("Para hoje") < msg.index("Próximos")


def test_a_mensagem_omite_as_secoes_sem_lead(enviadas, make_lead, today):
    make_lead(next_action_date=today)

    jobs.followup_job()

    msg = enviadas[0]
    assert "Para hoje" in msg
    assert "Atrasados" not in msg
    assert "Próximos" not in msg


def test_lead_sem_descricao_da_acao_nao_quebra_a_mensagem(enviadas, make_lead, today):
    make_lead(next_action=None, next_action_date=today)

    jobs.followup_job()

    assert "sem descrição" in enviadas[0]


def test_a_mensagem_traz_a_etapa_de_cada_lead(enviadas, make_lead, today):
    make_lead(stage=Stage.negociacao, next_action_date=today)

    jobs.followup_job()

    assert "negociacao" in enviadas[0]


def test_um_unico_envio_agrega_todos_os_leads(enviadas, make_lead, today):
    for i in range(5):
        make_lead(company_name=f"Empresa {i}", next_action_date=today)

    jobs.followup_job()

    assert len(enviadas) == 1
    for i in range(5):
        assert f"Empresa {i}" in enviadas[0]


def test_a_janela_de_antecedencia_e_configuravel(enviadas, make_lead, today, monkeypatch):
    monkeypatch.setattr(jobs.settings, "followup_days_ahead", 7)
    make_lead(company_name="Daqui a cinco dias", next_action_date=today + timedelta(days=5))

    jobs.followup_job()

    assert "Daqui a cinco dias" in enviadas[0]


def test_o_endpoint_manual_dispara_o_job(client, enviadas, make_lead, today):
    make_lead(next_action_date=today)

    r = client.post("/jobs/followup")

    assert r.status_code == 200
    assert r.json() == {"status": "executado"}
    assert len(enviadas) == 1


def test_o_endpoint_manual_funciona_com_o_pipeline_vazio(client, enviadas):
    r = client.post("/jobs/followup")

    assert r.status_code == 200
    assert enviadas == []
