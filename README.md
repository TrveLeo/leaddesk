# LeadDesk

Mini-CRM de pipeline comercial com prospecção acoplada. O projeto junta os
módulos de CRM e prospecção numa única aplicação FastAPI, com interface web
sem build servida pela própria API.

## Problema

Em operação comercial pequena, o problema raramente é "falta de ferramenta". É
histórico espalhado em WhatsApp, próxima ação sem dono, prospecção rodando em
planilha à parte e nenhuma visão única do caminho de prospect até cliente.

Isso gera quatro sintomas práticos:

- pipeline que parece vazio ou desatualizado
- follow-up perdido no meio da rotina
- prospecção sem meta semanal clara
- conversão de prospect para lead feita por cópia manual

## Solução

O LeadDesk resolve esse fluxo como um produto só:

- **pipeline de 8 etapas** com resumo por coluna e cards ordenados por urgência
- **detalhe do lead** com próxima ação, notas e histórico de interações aninhado
- **prospecção semanal** com metas visíveis de 20 pesquisadas e 10 contactadas
- **conversão prospect → lead** no mesmo sistema, sem duplicar cadastro
- **job de follow-up** para listar quem está atrasado, para hoje ou para amanhã

A interface foi feita em **HTML, CSS e JavaScript puros**, sem React, sem build
e sem CDN, no mesmo padrão que já funcionou no ConciliaFlow. `GET /` serve a
SPA estática e `/static/*` entrega os assets locais.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- HTML, CSS e JavaScript sem build
- Docker Compose
- Pytest

## Resultado

Os números do case saem de contagem de registro no banco e estão travados em
`demo/GABARITO.md` e `tests/test_seed.py`.

- **15,0%** de prospect pesquisado para lead `(18/120)`
- **30,0%** de prospect contatado para lead `(18/60)`
- **2,5%** de prospect pesquisado para cliente `(3/120)`
- **17 endpoints de negócio**
- **164 testes** com **100% de cobertura da aplicação** sobre `crm/`,
  `prospecting/` e `main.py`

O dataset de demonstração sobe sempre com a mesma distribuição:

- 120 prospects em 6 semanas
- 24 leads distribuídos nas 8 etapas
- 80 interações registradas
- 9 follow-ups dentro da janela diária padrão

Isso faz a tela nascer com volume real de uso, em vez de formulário vazio.

## Rodando localmente

```bash
docker compose up -d
docker compose exec api python scripts/seed_demo.py --reset
```

Depois:

- interface: `http://localhost:8001/`
- OpenAPI: `http://localhost:8001/docs`

## Estrutura

```text
crm/           leads, pipeline, interações e follow-up
prospecting/   prospects, métricas semanais e conversão
static/        interface web sem build
scripts/       seed de demonstração reproduzível
tests/         suíte automatizada
```

## Observações do case

- Todos os dados da demo são **fictícios**.
- O número de `17 endpoints` é o correto. `14` era uma contagem antiga.
- A interface foi pensada para o print do portfólio: pipeline cheio, detalhe de
  lead com histórico visível e metas semanais batidas nas seis semanas.
