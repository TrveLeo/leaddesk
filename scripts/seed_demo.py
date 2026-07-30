"""Gera o dataset de demonstração do LeadDesk.

**Dados 100% fictícios**, gerados por semente fixa — nenhuma empresa real, nem
anonimizada. O funil é montado por cotas explícitas, não por sorteio de status:
rodar de novo produz exatamente a mesma distribuição, e os números do
`demo/GABARITO.md` são conferidos em `tests/test_seed.py`.

Uso:
    python scripts/seed_demo.py            # popula o banco de DATABASE_URL
    python scripts/seed_demo.py --reset    # apaga tudo antes de popular

As datas são relativas a hoje, para que a demonstração nunca pareça vencida.
As **contagens** é que são fixas — e é sobre elas que o case fala.
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session  # noqa: E402

from crm.database import Base, SessionLocal, engine  # noqa: E402
from crm.models import Interaction, InteractionType, Lead, Source, Stage  # noqa: E402
from prospecting.models import Prospect, ProspectSource, ProspectStatus, Segment  # noqa: E402
from prospecting.routers.prospects import _map_source  # noqa: E402

SEED = 20260729

SEMANAS = 6
POR_SEMANA = 20

# Cota de status por semana. Soma 20 — a meta semanal de prospects pesquisados.
# `contactado` + `convertido` = 10, que é exatamente a meta de contatos.
COTA_SEMANAL = {
    ProspectStatus.descartado: 5,
    ProspectStatus.pesquisando: 2,
    ProspectStatus.qualificado: 3,
    ProspectStatus.contactado: 7,
    ProspectStatus.convertido: 3,
}

# Leads que não vieram da prospecção ativa — entraram por indicação e redes.
LEADS_DE_OUTROS_CANAIS = 6

# Onde os 24 leads param no pipeline de 8 etapas.
COTA_ETAPAS = {
    Stage.novo_contato: 4,
    Stage.qualificando: 5,
    Stage.reuniao_agendada: 4,
    Stage.proposta_enviada: 3,
    Stage.negociacao: 2,
    Stage.cliente: 3,
    Stage.acompanhamento: 2,
    Stage.sem_momento: 1,
}

# Quanto histórico cada etapa carrega. Quem está mais fundo conversou mais.
INTERACOES_POR_ETAPA = {
    Stage.novo_contato: 1,
    Stage.qualificando: 2,
    Stage.reuniao_agendada: 3,
    Stage.proposta_enviada: 4,
    Stage.negociacao: 5,
    Stage.cliente: 6,
    Stage.acompanhamento: 6,
    Stage.sem_momento: 2,
}

# Agenda de follow-up dos 20 leads que o job olha (cliente e sem_momento saem).
AGENDA = {
    "atrasado": 3,
    "hoje": 4,
    "amanha": 2,
    "futuro": 8,
    "sem_data": 3,
}

PREFIXOS = {
    Segment.contabilidade: ["Contabilidade", "Escritório Contábil", "Assessoria Contábil"],
    Segment.marketing: ["Agência", "Studio Criativo", "Marketing"],
    Segment.logistica: ["Transportadora", "Logística", "Expresso"],
    Segment.imobiliaria: ["Imobiliária", "Corretora", "Administradora Predial"],
    Segment.manutencao: ["Manutenção Predial", "Climatização", "Conservadora"],
    Segment.ecommerce: ["Loja", "Distribuidora", "Comércio"],
    Segment.consultoria: ["Consultoria", "Assessoria Empresarial", "Gestão"],
    Segment.servicos_tecnicos: ["Assistência Técnica", "Elétrica", "Automação"],
    Segment.outro: ["Empresa", "Grupo", "Central"],
}

NOMES_FANTASIA = [
    "Horizonte", "Vista Mar", "Praia Grande", "Rota Certa", "Ponto Alto",
    "Boa Vista", "Serra Azul", "Nova Era", "Primavera", "Atlântico",
    "Ilha do Sol", "Vale Verde", "Norte Sul", "Porto Novo", "Aurora",
    "Bandeirante", "Colina", "Estrela do Mar", "Guarapari", "Itaparica",
    "Jacaraípe", "Laranjeiras", "Manguinhos", "Novo Tempo", "Orion",
    "Pedra Azul", "Quatro Ventos", "Riviera", "Santa Clara", "Trilha",
    "União", "Vitória Régia", "Xodó", "Zenite", "Camburi", "Enseada",
]

CONTATOS = [
    "Marina Alves", "Rafael Pires", "Diego Moraes", "Bruna Sato", "Caio Ferraz",
    "Letícia Nunes", "Paulo Rangel", "Camila Duarte", "Tiago Bastos", "Aline Rocha",
    "Fernando Lima", "Juliana Prado", "Marcos Vieira", "Patrícia Gomes", "Rodrigo Serra",
    "Sabrina Coelho", "André Tavares", "Vanessa Braga", "Gustavo Neves", "Renata Campos",
    "Henrique Dias", "Isabela Fontes", "Leonardo Muniz", "Natália Reis", "Otávio Barros",
    "Priscila Amaral", "Ricardo Salles", "Tatiana Mendes", "Vitor Aragão", "Yara Cordeiro",
]

TAMANHOS = ["5-20", "20-50", "50-100", "100+"]

SINAIS = [
    "Controla pedidos em planilha compartilhada; retrabalho no fechamento.",
    "Time comercial sem CRM — histórico de contato vive no WhatsApp.",
    "Conciliação bancária manual, duas pessoas dedicadas meio período.",
    "Relatório mensal montado à mão a partir de três sistemas diferentes.",
    "Site sem integração com o estoque; ruptura descoberta pelo cliente.",
    "Emissão de nota em processo separado, com redigitação.",
    "Agenda de manutenção em papel; ordem de serviço se perde.",
    "Exporta CSV do ERP e reformata toda semana para a diretoria.",
]

MOTIVOS_DESCARTE = [
    "Sem orçamento para este exercício.",
    "Já contratou fornecedor no mês passado.",
    "Porte menor do que o perfil atendido.",
    "Sem interlocutor técnico — decisão travada.",
    "Não respondeu após três tentativas.",
]

ACOES = [
    "Enviar proposta revisada",
    "Confirmar reunião de diagnóstico",
    "Retomar contato após o fechamento do mês",
    "Enviar escopo detalhado",
    "Ligar para alinhar orçamento",
    "Mandar case de referência",
    "Agendar call com o time técnico",
]

DESCRICOES = {
    InteractionType.mensagem: [
        "Primeiro contato por WhatsApp, apresentação do escopo.",
        "Mensagem de retomada após uma semana sem resposta.",
        "Enviado material comercial por e-mail.",
    ],
    InteractionType.ligacao: [
        "Ligação de qualificação — mapeado o processo atual.",
        "Ligação rápida para confirmar o decisor.",
    ],
    InteractionType.reuniao: [
        "Reunião de diagnóstico, 45 min, com o time de operações.",
        "Call de alinhamento técnico sobre a integração.",
    ],
    InteractionType.proposta: [
        "Proposta enviada — pacote de automação, 3 parcelas.",
        "Proposta ajustada após pedido de redução de escopo.",
    ],
    InteractionType.follow_up: [
        "Follow-up da proposta enviada na semana anterior.",
        "Follow-up agendado pelo job diário.",
    ],
    InteractionType.outro: [
        "Recebida documentação de acesso ao sistema.",
    ],
}

# Origens de prospecção, na proporção em que aparecem na prática.
ORIGENS_PROSPECT = (
    [ProspectSource.google_maps] * 8
    + [ProspectSource.linkedin] * 5
    + [ProspectSource.indicacao] * 3
    + [ProspectSource.instagram] * 2
    + [ProspectSource.ex_colega] * 1
    + [ProspectSource.associacao] * 1
)

ORIGENS_OUTROS_CANAIS = [
    Source.indicacao,
    Source.indicacao,
    Source.linkedin,
    Source.whatsapp,
    Source.instagram,
    Source.plataforma,
]


def _segunda_da_semana(referencia: date) -> date:
    return referencia - timedelta(days=referencia.weekday())


def _gerador_de_nomes(rng: random.Random):
    """Devolve nomes de empresa únicos, sem repetir combinação."""
    usados: set[str] = set()

    def proximo(segment: Segment) -> str:
        while True:
            nome = f"{rng.choice(PREFIXOS[segment])} {rng.choice(NOMES_FANTASIA)}"
            if nome not in usados:
                usados.add(nome)
                return nome

    return proximo


def _telefone(rng: random.Random) -> str:
    return f"(27) 9{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}"


def _email(empresa: str, rng: random.Random) -> str:
    slug = (
        empresa.split()[-1]
        .lower()
        .translate(str.maketrans("áàâãéêíóôõúüç", "aaaaeeiooouuc"))
    )
    return f"contato@{slug}.com.br"


def semear(db: Session, hoje: date | None = None) -> dict[str, int]:
    """Popula o banco e devolve as contagens do gabarito."""
    hoje = hoje or date.today()
    rng = random.Random(SEED)
    proximo_nome = _gerador_de_nomes(rng)
    segunda_atual = _segunda_da_semana(hoje)

    segmentos = list(Segment)
    convertidos: list[Prospect] = []

    # --- prospects: 6 semanas × 20, com cota de status fixa por semana ---
    for indice_semana in range(SEMANAS):
        semana = segunda_atual - timedelta(weeks=SEMANAS - 1 - indice_semana)

        status_da_semana: list[ProspectStatus] = []
        for status, quantidade in COTA_SEMANAL.items():
            status_da_semana.extend([status] * quantidade)
        rng.shuffle(status_da_semana)

        for status in status_da_semana:
            segmento = rng.choice(segmentos[:-1])  # `outro` fica de fora do sorteio
            empresa = proximo_nome(segmento)
            prospect = Prospect(
                company_name=empresa,
                segment=segmento,
                size_estimate=rng.choice(TAMANHOS),
                source=rng.choice(ORIGENS_PROSPECT),
                contact_name=rng.choice(CONTATOS),
                phone=_telefone(rng),
                email=_email(empresa, rng),
                signals=rng.choice(SINAIS),
                status=status,
                week=semana,
                notes=None,
            )

            if status in {ProspectStatus.contactado, ProspectStatus.convertido}:
                prospect.contacted_at = semana + timedelta(days=rng.randint(1, 4))
            if status is ProspectStatus.descartado:
                prospect.discard_reason = rng.choice(MOTIVOS_DESCARTE)

            db.add(prospect)
            if status is ProspectStatus.convertido:
                convertidos.append(prospect)

    db.flush()

    # --- leads: os convertidos, mais os que entraram por outros canais ---
    leads: list[Lead] = []

    for prospect in convertidos:
        lead = Lead(
            company_name=prospect.company_name,
            contact_name=prospect.contact_name,
            phone=prospect.phone,
            email=prospect.email,
            source=_map_source(prospect.source.value),
            stage=Stage.qualificando,  # ajustado abaixo pela cota de etapas
            notes=prospect.signals,
        )
        db.add(lead)
        db.flush()
        prospect.lead_id = lead.id
        leads.append(lead)

    for origem in ORIGENS_OUTROS_CANAIS:
        segmento = rng.choice(segmentos[:-1])
        empresa = proximo_nome(segmento)
        lead = Lead(
            company_name=empresa,
            contact_name=rng.choice(CONTATOS),
            phone=_telefone(rng),
            email=_email(empresa, rng),
            source=origem,
            stage=Stage.novo_contato,
            notes=rng.choice(SINAIS),
        )
        db.add(lead)
        leads.append(lead)

    db.flush()

    # --- distribui os 24 leads pelas 8 etapas, por cota ---
    etapas: list[Stage] = []
    for stage, quantidade in COTA_ETAPAS.items():
        etapas.extend([stage] * quantidade)
    rng.shuffle(etapas)
    for lead, stage in zip(leads, etapas, strict=True):
        lead.stage = stage

    # --- histórico de interações, proporcional à profundidade da etapa ---
    total_interacoes = 0
    for lead in leads:
        quantas = INTERACOES_POR_ETAPA[lead.stage]
        for passo in range(quantas):
            tipo = list(DESCRICOES)[min(passo, len(DESCRICOES) - 1)]
            db.add(
                Interaction(
                    lead_id=lead.id,
                    type=tipo,
                    description=rng.choice(DESCRICOES[tipo]),
                    date=hoje - timedelta(days=(quantas - passo) * 5),
                )
            )
            total_interacoes += 1

    # --- agenda de follow-up dos leads que o job enxerga ---
    ativos = [l for l in leads if l.stage not in {Stage.cliente, Stage.sem_momento}]
    rng.shuffle(ativos)

    slots: list[str] = []
    for quando, quantidade in AGENDA.items():
        slots.extend([quando] * quantidade)

    for lead, quando in zip(ativos, slots, strict=True):
        if quando == "sem_data":
            continue
        lead.next_action = rng.choice(ACOES)
        lead.next_action_date = {
            "atrasado": hoje - timedelta(days=rng.randint(1, 6)),
            "hoje": hoje,
            "amanha": hoje + timedelta(days=1),
            "futuro": hoje + timedelta(days=rng.randint(3, 21)),
        }[quando]

    db.commit()

    return {
        "prospects": SEMANAS * POR_SEMANA,
        "semanas": SEMANAS,
        "convertidos": len(convertidos),
        "leads": len(leads),
        "interacoes": total_interacoes,
        "followups_pendentes": AGENDA["atrasado"] + AGENDA["hoje"] + AGENDA["amanha"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true", help="apaga as tabelas antes de popular"
    )
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(Prospect).count() or db.query(Lead).count():
            print("Banco já tem dados. Use --reset para recomeçar.")
            raise SystemExit(1)
        numeros = semear(db)
    finally:
        db.close()

    print("Dataset de demonstração gerado (semente fixa " f"{SEED}):")
    for chave, valor in numeros.items():
        print(f"  {chave:22} {valor}")


if __name__ == "__main__":
    main()
