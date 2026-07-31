"""Dataset de demonstração: os números do case saem daqui.

Cada valor conferido aqui aparece em `demo/GABARITO.md` e no README. Se um
teste destes quebrar, o texto do case está desatualizado — não o contrário.
"""

from datetime import date, timedelta

import pytest

from crm.models import Interaction, Lead, Stage
from prospecting.models import Prospect, ProspectStatus
from scripts import seed_demo
from scripts.seed_demo import SEED, semear

HOJE = date(2026, 7, 29)  # quarta-feira — data fixa para os testes de agenda


@pytest.fixture
def semeado(db):
    return semear(db, hoje=HOJE)


def test_o_seed_devolve_as_contagens_do_gabarito(semeado):
    assert semeado == {
        "prospects": 120,
        "semanas": 6,
        "convertidos": 18,
        "leads": 24,
        "interacoes": 80,
        "followups_pendentes": 9,
    }


def test_gera_cento_e_vinte_prospects_em_seis_semanas(semeado, db):
    assert db.query(Prospect).count() == 120
    assert db.query(Prospect.week).distinct().count() == 6


def test_cada_semana_tem_vinte_prospects(semeado, db):
    semanas = [w for (w,) in db.query(Prospect.week).distinct()]

    for semana in semanas:
        assert db.query(Prospect).filter(Prospect.week == semana).count() == 20


def test_toda_semana_e_uma_segunda_feira(semeado, db):
    for (semana,) in db.query(Prospect.week).distinct():
        assert semana.weekday() == 0


def test_a_distribuicao_de_status_e_a_cota_esperada(semeado, db):
    contagem = {
        status: db.query(Prospect).filter(Prospect.status == status).count()
        for status in ProspectStatus
    }

    assert contagem == {
        ProspectStatus.pesquisando: 12,
        ProspectStatus.qualificado: 18,
        ProspectStatus.contactado: 42,
        ProspectStatus.convertido: 18,
        ProspectStatus.descartado: 30,
    }


def test_a_meta_semanal_de_contatos_e_atingida_em_toda_semana(semeado, client, db):
    """`contactado` + `convertido` = 10 por semana, que é a meta do plano."""
    for (semana,) in db.query(Prospect.week).distinct():
        body = client.get("/prospects/week/stats", params={"week": semana.isoformat()}).json()

        assert body["total"] == 20
        assert body["total"] >= body["meta_pesquisadas"]
        assert body["contactado"] + body["convertido"] == body["meta_contactadas"]


def test_taxa_de_conversao_do_topo_do_funil_e_quinze_por_cento(semeado, db):
    prospects = db.query(Prospect).count()
    convertidos = db.query(Prospect).filter(Prospect.status == ProspectStatus.convertido).count()

    assert convertidos / prospects == 0.15


def test_taxa_de_conversao_sobre_contactados_e_trinta_por_cento(semeado, db):
    contactados = (
        db.query(Prospect)
        .filter(Prospect.status.in_([ProspectStatus.contactado, ProspectStatus.convertido]))
        .count()
    )
    convertidos = db.query(Prospect).filter(Prospect.status == ProspectStatus.convertido).count()

    assert contactados == 60
    assert convertidos / contactados == 0.30


def test_gera_vinte_e_quatro_leads(semeado, db):
    assert db.query(Lead).count() == 24


def test_dezoito_leads_vieram_da_prospeccao_e_seis_de_outros_canais(semeado, db):
    com_prospect = db.query(Prospect).filter(Prospect.lead_id.isnot(None)).count()

    assert com_prospect == 18
    assert db.query(Lead).count() - com_prospect == 6


def test_todo_prospect_convertido_aponta_para_um_lead_que_existe(semeado, db):
    convertidos = db.query(Prospect).filter(Prospect.status == ProspectStatus.convertido).all()

    assert len(convertidos) == 18
    for prospect in convertidos:
        assert prospect.lead_id is not None
        lead = db.get(Lead, prospect.lead_id)
        assert lead is not None
        assert lead.company_name == prospect.company_name


def test_nenhum_prospect_nao_convertido_aponta_para_lead(semeado, db):
    outros = db.query(Prospect).filter(Prospect.status != ProspectStatus.convertido).all()

    assert all(p.lead_id is None for p in outros)


def test_as_oito_etapas_do_pipeline_tem_lead(semeado, client):
    resumo = client.get("/leads/pipeline/summary").json()

    assert resumo == {
        "novo_contato": 4,
        "qualificando": 5,
        "reuniao_agendada": 4,
        "proposta_enviada": 3,
        "negociacao": 2,
        "cliente": 3,
        "acompanhamento": 2,
        "sem_momento": 1,
    }
    assert sum(resumo.values()) == 24
    assert all(quantidade > 0 for quantidade in resumo.values())


def test_tres_clientes_fechados_saem_de_cento_e_vinte_prospects(semeado, db):
    clientes = db.query(Lead).filter(Lead.stage == Stage.cliente).count()

    assert clientes == 3
    assert clientes / db.query(Prospect).count() == 0.025


def test_gera_oitenta_interacoes(semeado, db):
    assert db.query(Interaction).count() == 80


def test_todo_lead_tem_pelo_menos_uma_interacao(semeado, db):
    for lead in db.query(Lead).all():
        assert len(lead.interactions) >= 1


def test_lead_mais_fundo_no_funil_tem_mais_historico(semeado, db):
    def historico(stage: Stage) -> int:
        leads = db.query(Lead).filter(Lead.stage == stage).all()
        return len(leads[0].interactions)

    assert historico(Stage.novo_contato) == 1
    assert historico(Stage.qualificando) == 2
    assert historico(Stage.proposta_enviada) == 4
    assert historico(Stage.cliente) == 6


def test_nove_leads_entram_no_follow_up_de_hoje(semeado, db, monkeypatch):
    """3 atrasados + 4 para hoje + 2 para amanhã, dentro da janela padrão."""
    from crm import jobs

    enviadas: list[str] = []
    monkeypatch.setattr(jobs, "send_telegram", lambda msg: enviadas.append(msg) or True)
    monkeypatch.setattr(jobs, "date", _DataFixa)

    jobs.followup_job()

    assert len(enviadas) == 1
    linhas = [l for l in enviadas[0].splitlines() if l.startswith("•")]
    assert len(linhas) == 9


def test_nenhum_cliente_ou_sem_momento_recebe_follow_up(semeado, db):
    ignorados = db.query(Lead).filter(Lead.stage.in_([Stage.cliente, Stage.sem_momento])).all()

    assert len(ignorados) == 4
    assert all(lead.next_action_date is None for lead in ignorados)


def test_tres_leads_ativos_ficam_sem_data_de_proxima_acao(semeado, db):
    ativos = db.query(Lead).filter(Lead.stage.notin_([Stage.cliente, Stage.sem_momento])).all()
    sem_data = [lead for lead in ativos if lead.next_action_date is None]

    assert len(ativos) == 20
    assert len(sem_data) == 3


def test_os_nomes_de_empresa_nao_se_repetem(semeado, db):
    nomes = [nome for (nome,) in db.query(Prospect.company_name).all()]
    nomes += [nome for (nome,) in db.query(Lead.company_name).all()]

    prospectados = {nome for (nome,) in db.query(Prospect.company_name).all()}
    assert len(prospectados) == 120
    # os 18 leads convertidos repetem o nome do prospect de origem, de propósito
    assert len(set(nomes)) == 120 + 6


def test_rodar_duas_vezes_produz_os_mesmos_dados(db):
    primeira = semear(db, hoje=HOJE)
    nomes_1 = [n for (n,) in db.query(Prospect.company_name).order_by(Prospect.id).all()]

    for tabela in (Interaction, Lead, Prospect):
        db.query(tabela).delete()
    db.commit()

    segunda = semear(db, hoje=HOJE)
    nomes_2 = [n for (n,) in db.query(Prospect.company_name).order_by(Prospect.id).all()]

    assert primeira == segunda
    assert nomes_1 == nomes_2


def test_a_semente_esta_fixa_no_modulo():
    assert SEED == 20260729


class _DataFixa(date):
    """Congela `date.today()` no dia de referência do seed."""

    @classmethod
    def today(cls) -> date:
        return HOJE


def test_a_linha_de_comando_popula_e_relata_os_numeros(capsys, monkeypatch, db):
    monkeypatch.setattr("sys.argv", ["seed_demo.py", "--reset"])

    seed_demo.main()

    saida = capsys.readouterr().out
    assert "120" in saida and "24" in saida
    assert str(SEED) in saida
    assert db.query(Prospect).count() == 120


def test_a_linha_de_comando_recusa_sobrescrever_banco_com_dado(capsys, monkeypatch, db):
    semear(db, hoje=HOJE)
    monkeypatch.setattr("sys.argv", ["seed_demo.py"])

    with pytest.raises(SystemExit) as saiu:
        seed_demo.main()

    assert saiu.value.code == 1
    assert "Use --reset" in capsys.readouterr().out
    assert db.query(Prospect).count() == 120  # não duplicou


def test_as_semanas_terminam_na_semana_corrente(semeado, db):
    semanas = sorted(w for (w,) in db.query(Prospect.week).distinct())
    segunda_de_hoje = HOJE - timedelta(days=HOJE.weekday())

    assert semanas[-1] == segunda_de_hoje
    assert semanas[0] == segunda_de_hoje - timedelta(weeks=5)


def test_as_cotas_variam_entre_as_semanas(semeado, db):
    """O painel de evolução do dashboard precisa de movimento para dizer algo.

    Cotas idênticas nas seis semanas produziam duas retas no gráfico de
    histórico. A progressão plantada é a de uma operação que aprende: descarte
    caindo, qualificação e conversão subindo. Os números aqui são os do
    `demo/GABARITO.md`.
    """
    semanas = sorted(w for (w,) in db.query(Prospect.week).distinct())

    def por_semana(status):
        return [
            db.query(Prospect)
            .filter(Prospect.week == semana, Prospect.status == status)
            .count()
            for semana in semanas
        ]

    assert por_semana(ProspectStatus.convertido) == [2, 2, 3, 3, 4, 4]
    assert por_semana(ProspectStatus.descartado) == [6, 6, 5, 5, 4, 4]
    assert por_semana(ProspectStatus.qualificado) == [2, 2, 3, 3, 4, 4]
    assert por_semana(ProspectStatus.contactado) == [8, 8, 7, 7, 6, 6]
    assert por_semana(ProspectStatus.pesquisando) == [2, 2, 2, 2, 2, 2]


def test_a_meta_de_contatos_e_o_unico_valor_fixo_entre_semanas(semeado, db):
    """O que não pode variar: `contactado + convertido` bate a meta toda semana."""
    semanas = sorted(w for (w,) in db.query(Prospect.week).distinct())

    for semana in semanas:
        contatados = (
            db.query(Prospect)
            .filter(
                Prospect.week == semana,
                Prospect.status.in_([ProspectStatus.contactado, ProspectStatus.convertido]),
            )
            .count()
        )
        assert contatados == seed_demo.META_CONTATOS
