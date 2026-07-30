"""Importação de prospects por CSV."""

import csv
from datetime import date

import pytest

from prospecting.models import Prospect, ProspectSource, ProspectStatus, Segment
from scripts import import_prospects
from scripts.import_prospects import importar, ler_csv, segunda_da_semana

SEMANA = date(2026, 8, 3)  # segunda-feira


def escrever_csv(caminho, linhas, colunas=None):
    colunas = colunas or list(linhas[0])
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(linhas)
    return caminho


def test_importa_uma_linha_minima(db):
    resultado = importar(db, [{"company_name": "Limacont Contabilidade"}], semana=SEMANA)

    assert resultado.importados == ["Limacont Contabilidade"]
    prospect = db.query(Prospect).one()
    assert prospect.company_name == "Limacont Contabilidade"
    assert prospect.status == ProspectStatus.pesquisando
    assert prospect.week == SEMANA


def test_prospect_importado_nasce_em_pesquisando(db):
    importar(db, [{"company_name": "Empresa", "status": "convertido"}], semana=SEMANA)

    assert db.query(Prospect).one().status == ProspectStatus.pesquisando


def test_origem_padrao_e_google_maps(db):
    """A busca automatizada sai do OpenStreetMap, que é a mesma natureza de fonte."""
    importar(db, [{"company_name": "Empresa"}], semana=SEMANA)

    assert db.query(Prospect).one().source == ProspectSource.google_maps


def test_aceita_segmento_e_origem_validos(db):
    importar(
        db,
        [{"company_name": "Transportes X", "segment": "logistica", "source": "linkedin"}],
        semana=SEMANA,
    )

    prospect = db.query(Prospect).one()
    assert prospect.segment == Segment.logistica
    assert prospect.source == ProspectSource.linkedin


def test_segmento_invalido_vira_outro_em_vez_de_quebrar(db):
    importar(db, [{"company_name": "Empresa", "segment": "mineracao_espacial"}], semana=SEMANA)

    assert db.query(Prospect).one().segment == Segment.outro


def test_origem_invalida_cai_no_padrao(db):
    importar(db, [{"company_name": "Empresa", "source": "pombo_correio"}], semana=SEMANA)

    assert db.query(Prospect).one().source == ProspectSource.google_maps


def test_segmento_aceita_maiuscula_e_espaco(db):
    importar(db, [{"company_name": "Empresa", "segment": "  Contabilidade "}], semana=SEMANA)

    assert db.query(Prospect).one().segment == Segment.contabilidade


def test_preenche_os_campos_de_texto(db):
    importar(
        db,
        [{
            "company_name": "Imobiliária Realize",
            "contact_name": "Rafael Pires",
            "phone": "+55 27 3535 3044",
            "email": "contato@realize.com.br",
            "signals": "Planilha manual de visitas.",
            "notes": "Indicada por ex-colega.",
            "size_estimate": "20-50",
        }],
        semana=SEMANA,
    )

    prospect = db.query(Prospect).one()
    assert prospect.contact_name == "Rafael Pires"
    assert prospect.phone == "+55 27 3535 3044"
    assert prospect.signals == "Planilha manual de visitas."
    assert prospect.size_estimate == "20-50"


def test_campo_vazio_nao_sobrescreve_com_string_vazia(db):
    importar(db, [{"company_name": "Empresa", "contact_name": "", "phone": "  "}], semana=SEMANA)

    prospect = db.query(Prospect).one()
    assert prospect.contact_name is None
    assert prospect.phone is None


def test_colunas_desconhecidas_sao_ignoradas(db):
    """O CSV da busca traz endereço, link do OSM e coordenadas — não atrapalham."""
    importar(
        db,
        [{
            "company_name": "Empresa",
            "osm": "https://www.openstreetmap.org/node/123",
            "lat": "-20.31",
            "lon": "-40.31",
            "sinal_automatico": "sem site cadastrado",
            "segmento_deduzido": "sim",
        }],
        semana=SEMANA,
    )

    assert db.query(Prospect).count() == 1


def test_linha_sem_nome_e_ignorada_com_o_numero_da_linha(db):
    resultado = importar(
        db, [{"company_name": ""}, {"company_name": "Válida"}], semana=SEMANA
    )

    assert resultado.ignorados == [(2, "sem company_name")]
    assert resultado.importados == ["Válida"]
    assert db.query(Prospect).count() == 1


def test_nao_duplica_empresa_ja_cadastrada(db, make_prospect):
    make_prospect(company_name="Limacont Contabilidade")

    resultado = importar(db, [{"company_name": "Limacont Contabilidade"}], semana=SEMANA)

    assert resultado.repetidos == ["Limacont Contabilidade"]
    assert db.query(Prospect).count() == 1


def test_deduplicacao_ignora_caixa(db, make_prospect):
    make_prospect(company_name="Limacont Contabilidade")

    resultado = importar(db, [{"company_name": "LIMACONT CONTABILIDADE"}], semana=SEMANA)

    assert len(resultado.repetidos) == 1
    assert db.query(Prospect).count() == 1


def test_deduplica_dentro_do_proprio_csv(db):
    resultado = importar(
        db,
        [{"company_name": "Repetida"}, {"company_name": "repetida"}],
        semana=SEMANA,
    )

    assert len(resultado.importados) == 1
    assert len(resultado.repetidos) == 1
    assert db.query(Prospect).count() == 1


def test_semana_da_linha_tem_prioridade_sobre_a_do_comando(db):
    importar(db, [{"company_name": "Empresa", "week": "2026-07-29"}], semana=SEMANA)

    assert db.query(Prospect).one().week == date(2026, 7, 27)  # segunda daquela semana


def test_week_invalida_ignora_a_linha_e_diz_por_que(db):
    resultado = importar(db, [{"company_name": "Empresa", "week": "ontem"}], semana=SEMANA)

    assert resultado.ignorados == [(2, "week invalida: ontem")]
    assert db.query(Prospect).count() == 0


def test_dry_run_nao_grava_nada(db):
    resultado = importar(
        db, [{"company_name": "Empresa"}], semana=SEMANA, dry_run=True
    )

    assert resultado.importados == ["Empresa"]
    assert db.query(Prospect).count() == 0


def test_dry_run_detecta_repetido_sem_gravar(db, make_prospect):
    make_prospect(company_name="Já existe")

    resultado = importar(
        db,
        [{"company_name": "Já existe"}, {"company_name": "Nova"}],
        semana=SEMANA,
        dry_run=True,
    )

    assert resultado.repetidos == ["Já existe"]
    assert resultado.importados == ["Nova"]
    assert db.query(Prospect).count() == 1


def test_o_total_soma_as_tres_categorias(db, make_prospect):
    make_prospect(company_name="Repetida")

    resultado = importar(
        db,
        [{"company_name": "Repetida"}, {"company_name": "Nova"}, {"company_name": ""}],
        semana=SEMANA,
    )

    assert resultado.total == 3


def test_a_semana_e_sempre_normalizada_para_segunda():
    assert segunda_da_semana(date(2026, 8, 5)).weekday() == 0  # quarta -> segunda
    assert segunda_da_semana(date(2026, 8, 3)) == date(2026, 8, 3)  # já é segunda
    assert segunda_da_semana(date(2026, 8, 9)) == date(2026, 8, 3)  # domingo


def test_le_csv_do_disco(tmp_path):
    caminho = escrever_csv(
        tmp_path / "lista.csv",
        [{"company_name": "Empresa A", "segment": "contabilidade"}],
    )

    linhas = ler_csv(caminho)

    assert linhas == [{"company_name": "Empresa A", "segment": "contabilidade"}]


def test_csv_sem_a_coluna_obrigatoria_falha_cedo(tmp_path):
    caminho = escrever_csv(tmp_path / "ruim.csv", [{"nome": "Empresa A"}])

    with pytest.raises(SystemExit, match="company_name"):
        ler_csv(caminho)


def test_csv_vazio_nao_quebra(tmp_path, db):
    caminho = tmp_path / "vazio.csv"
    caminho.write_text("company_name\n", encoding="utf-8")

    assert importar(db, ler_csv(caminho), semana=SEMANA).total == 0


def test_importados_aparecem_nas_metricas_da_semana(db, client):
    semana = segunda_da_semana()
    importar(db, [{"company_name": f"Empresa {i}"} for i in range(20)], semana=semana)

    body = client.get("/prospects/week/stats").json()

    assert body["total"] == 20
    assert body["pesquisando"] == 20
    assert body["total"] >= body["meta_pesquisadas"]


def test_a_linha_de_comando_importa_de_verdade(tmp_path, db, monkeypatch, capsys):
    caminho = escrever_csv(
        tmp_path / "lista.csv", [{"company_name": "Via CLI", "segment": "logistica"}]
    )
    monkeypatch.setattr("sys.argv", ["import_prospects.py", str(caminho)])

    import_prospects.main()

    assert "1 importados" in capsys.readouterr().out
    assert db.query(Prospect).one().company_name == "Via CLI"


def test_a_linha_de_comando_respeita_o_dry_run(tmp_path, db, monkeypatch, capsys):
    caminho = escrever_csv(tmp_path / "lista.csv", [{"company_name": "Não grava"}])
    monkeypatch.setattr("sys.argv", ["import_prospects.py", str(caminho), "--dry-run"])

    import_prospects.main()

    saida = capsys.readouterr().out
    assert "simulação" in saida
    assert "Nada foi gravado" in saida
    assert db.query(Prospect).count() == 0


def test_a_linha_de_comando_aceita_semana_e_relata_o_ignorado(
    tmp_path, db, monkeypatch, capsys
):
    caminho = escrever_csv(
        tmp_path / "lista.csv",
        [{"company_name": "Com semana"}, {"company_name": ""}],
    )
    monkeypatch.setattr(
        "sys.argv", ["import_prospects.py", str(caminho), "--week", "2026-08-05"]
    )

    import_prospects.main()

    saida = capsys.readouterr().out
    assert "linha 3: sem company_name" in saida
    assert db.query(Prospect).one().week == date(2026, 8, 3)  # quarta -> segunda


def test_a_linha_de_comando_recusa_arquivo_inexistente(monkeypatch):
    monkeypatch.setattr("sys.argv", ["import_prospects.py", "/nao/existe.csv"])

    with pytest.raises(SystemExit, match="não encontrado"):
        import_prospects.main()
