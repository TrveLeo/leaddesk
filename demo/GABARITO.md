# Gabarito do dataset de demonstração

**Dados fictícios**, gerados por `scripts/seed_demo.py` com semente `20260729`.
Nenhuma empresa real, nem anonimizada. Rodar de novo produz exatamente a mesma
distribuição.

```bash
python scripts/seed_demo.py --reset
```

As **datas** são relativas ao dia da execução, para que a demonstração nunca
pareça vencida. As **contagens** são fixas — e é sobre elas que o case fala.
Todas são conferidas em `tests/test_seed.py`: se um número aqui estiver errado,
a suíte quebra.

---

## Volume gerado

| Item | Qtd |
|---|---|
| Prospects | 120 |
| Semanas de prospecção | 6 |
| Leads | 24 |
| Interações registradas | 80 |

Seis semanas × 20 prospects. A meta semanal do plano é 20 pesquisados e 10
contatados — o dataset a cumpre em **todas** as seis semanas, por construção.

## Funil de prospecção

| Status | Total | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|---|
| Pesquisando | 12 | 2 | 2 | 2 | 2 | 2 | 2 |
| Qualificado | 18 | 2 | 2 | 3 | 3 | 4 | 4 |
| Contactado | 42 | 8 | 8 | 7 | 7 | 6 | 6 |
| Convertido em lead | 18 | 2 | 2 | 3 | 3 | 4 | 4 |
| Descartado | 30 | 6 | 6 | 5 | 5 | 4 | 4 |
| **Total** | **120** | **20** | **20** | **20** | **20** | **20** | **20** |

`contactado + convertido = 10` em **todas** as semanas: a meta de contatos,
batida na régua. Esse é o número que fica fixo — os demais variam de propósito.

A progressão é a de uma operação que aprende: descarte caindo de 6 para 4,
qualificação e conversão subindo de 2 para 4, cadência de contato mantida na
meta o tempo todo. Cotas idênticas nas seis semanas seriam mais simples, mas
deixavam o painel de evolução do dashboard como duas retas — tecnicamente
corretas e inúteis como demonstração.

## As três taxas do case

| Taxa | Cálculo | Resultado |
|---|---|---|
| Prospect pesquisado → lead | 18 / 120 | **15,0%** |
| Prospect contatado → lead | 18 / 60 | **30,0%** |
| Prospect pesquisado → cliente | 3 / 120 | **2,5%** |

São contagens de registros no banco, não estimativa. Reproduzíveis com um
comando.

## Pipeline de leads

Os 24 leads ocupam **todas** as 8 etapas — nenhuma fica vazia, senão a tela do
pipeline não demonstra nada.

| Etapa | Leads | Interações por lead |
|---|---|---|
| Novo contato | 4 | 1 |
| Qualificando | 5 | 2 |
| Reunião agendada | 4 | 3 |
| Proposta enviada | 3 | 4 |
| Negociação | 2 | 5 |
| Cliente | 3 | 6 |
| Acompanhamento | 2 | 6 |
| Sem momento | 1 | 2 |
| **Total** | **24** | **80 interações** |

Quem está mais fundo no funil carrega mais histórico — é o que faz a tela de
detalhe do lead parecer um CRM em uso, e não um formulário recém-preenchido.

### De onde vieram os 24 leads

| Origem | Qtd |
|---|---|
| Convertidos da prospecção ativa | 18 |
| Indicação, LinkedIn, WhatsApp, Instagram, plataforma | 6 |

Os 18 convertidos guardam `lead_id` apontando para o lead criado, e herdam
nome, contato e sinais observados do prospect de origem. A origem do prospect é
traduzida para a origem do lead pelo mesmo mapa que a API usa
(`google_maps` → `prospeccao_ativa`, `ex_colega` → `indicacao`, e assim por
diante).

## Agenda de follow-up

Dos 24 leads, o job diário enxerga 20 — `cliente` e `sem momento` são pulados
de propósito, porque follow-up automático em quem já fechou ou já disse não é
ruído.

| Situação | Leads |
|---|---|
| Ação atrasada | 3 |
| Ação para hoje | 4 |
| Ação para amanhã | 2 |
| Ação futura (fora da janela) | 8 |
| Sem próxima ação definida | 3 |
| **Total de leads ativos** | **20** |

Com a janela padrão (`FOLLOWUP_DAYS_AHEAD=1`), rodar `POST /jobs/followup`
notifica **9 leads** — os 3 atrasados, os 4 de hoje e os 2 de amanhã. Os 8 de
data futura e os 3 sem data ficam de fora.

## O que foi plantado de propósito

| Situação | Por quê |
|---|---|
| 3 leads sem próxima ação definida | Mostra o buraco que o CRM ajuda a enxergar |
| 30 prospects descartados, com motivo escrito | Descarte com justificativa é dado, não desistência |
| Nomes de empresa nunca repetidos entre prospects | 120 nomes distintos — nada de "Empresa 47" |
| Lead convertido repete o nome do prospect | É a mesma empresa; o vínculo tem que ser visível |
| Sinais observados viram as notas do lead | O que foi visto na pesquisa não se perde na conversão |

## Cobertura

A suíte tem **199 testes** e cobre **100%** de `crm/`, `prospecting/` e
`main.py` (493 linhas), mais 99% de `scripts/seed_demo.py` — a única linha de
fora é o `if __name__ == "__main__"`.

```bash
pytest
```
