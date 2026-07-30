const STAGES = [
  ["novo_contato", "Novo contato", "Entrada do funil"],
  ["qualificando", "Qualificando", "Diagnóstico inicial"],
  ["reuniao_agendada", "Reunião agendada", "Próximo passo marcado"],
  ["proposta_enviada", "Proposta enviada", "Escopo na mesa"],
  ["negociacao", "Negociação", "Ajustes finais"],
  ["cliente", "Cliente", "Contrato fechado"],
  ["acompanhamento", "Acompanhamento", "Pós-venda e expansão"],
  ["sem_momento", "Sem momento", "Sem timing agora"],
];

const SOURCE_LABELS = {
  linkedin: "LinkedIn",
  instagram: "Instagram",
  whatsapp: "WhatsApp",
  indicacao: "Indicação",
  prospeccao_ativa: "Prospecção ativa",
  plataforma: "Plataforma",
  outro: "Outro canal",
};

const PROSPECT_SOURCE_LABELS = {
  google_maps: "Google Maps",
  linkedin: "LinkedIn",
  instagram: "Instagram",
  indicacao: "Indicação",
  ex_colega: "Ex-colega",
  fornecedor: "Fornecedor",
  associacao: "Associação",
  outro: "Outro",
};

const STATUS_LABELS = {
  pesquisando: "Pesquisando",
  qualificado: "Qualificado",
  contactado: "Contactado",
  convertido: "Convertido",
  descartado: "Descartado",
};

const SEGMENT_LABELS = {
  contabilidade: "Contabilidade",
  marketing: "Marketing",
  logistica: "Logística",
  imobiliaria: "Imobiliária",
  manutencao: "Manutenção",
  ecommerce: "E-commerce",
  consultoria: "Consultoria",
  servicos_tecnicos: "Serviços técnicos",
  outro: "Outro",
};

const INTERACTION_LABELS = {
  mensagem: "Mensagem",
  ligacao: "Ligação",
  reuniao: "Reunião",
  proposta: "Proposta",
  follow_up: "Follow-up",
  outro: "Outro",
};

const FOCUS_LABELS = {
  all: "Sem filtros ativos",
  urgent: "Filtro: ações atrasadas, hoje ou amanhã",
  rich: "Filtro: leads com histórico mais profundo",
  converted: "Filtro: oportunidades vindas da prospecção ativa",
  no_date: "Filtro: leads sem próxima ação definida",
};

const state = {
  summary: {},
  leads: [],
  leadDetails: new Map(),
  selectedLeadId: null,
  prospects: [],
  weeklyStats: new Map(),
  weeks: [],
  selectedWeek: null,
  selectedProspectId: null,
  search: "",
  focusFilter: "all",
  lastUpdated: null,
};

const elements = {
  board: document.querySelector("#pipeline-board"),
  pipelineTotal: document.querySelector("#pipeline-total"),
  refreshAll: document.querySelector("#refresh-all"),
  leadDetail: document.querySelector("#lead-detail"),
  leadDetailTitle: document.querySelector("#lead-detail-title"),
  leadDetailStage: document.querySelector("#lead-detail-stage"),
  statLeads: document.querySelector("#stat-leads"),
  statInteractions: document.querySelector("#stat-interactions"),
  statConverted: document.querySelector("#stat-converted"),
  statFollowups: document.querySelector("#stat-followups"),
  statLeadsDelta: document.querySelector("#stat-leads-delta"),
  statFollowupsDelta: document.querySelector("#stat-followups-delta"),
  statInteractionsDelta: document.querySelector("#stat-interactions-delta"),
  statConvertedDelta: document.querySelector("#stat-converted-delta"),
  weekSelect: document.querySelector("#week-select"),
  selectedWeekLabel: document.querySelector("#selected-week-label"),
  weeklyKpis: document.querySelector("#weekly-kpis"),
  weeklyBars: document.querySelector("#weekly-bars"),
  historyChart: document.querySelector("#history-chart"),
  prospectList: document.querySelector("#prospect-list"),
  conversionCount: document.querySelector("#conversion-count"),
  conversionForm: document.querySelector("#conversion-form"),
  convertCompany: document.querySelector("#convert-company"),
  convertContactName: document.querySelector("#convert-contact-name"),
  convertPhone: document.querySelector("#convert-phone"),
  convertEmail: document.querySelector("#convert-email"),
  convertNotes: document.querySelector("#convert-notes"),
  convertSubmit: document.querySelector("#convert-submit"),
  convertClear: document.querySelector("#convert-clear"),
  conversionFeedback: document.querySelector("#conversion-feedback"),
  leadCardTemplate: document.querySelector("#lead-card-template"),
  executiveSummary: document.querySelector("#executive-summary"),
  featureHeadline: document.querySelector("#feature-headline"),
  featureText: document.querySelector("#feature-text"),
  pipelineStrip: document.querySelector("#pipeline-strip"),
  summaryTag: document.querySelector("#summary-tag"),
  insightList: document.querySelector("#insight-list"),
  activityFeed: document.querySelector("#activity-feed"),
  dashboardStatus: document.querySelector("#dashboard-status"),
  lastUpdated: document.querySelector("#last-updated"),
  leadSearch: document.querySelector("#lead-search"),
  focusFilter: document.querySelector("#focus-filter"),
  activeFilters: document.querySelector("#active-filters"),
  statAlerts: document.querySelector("#stat-alerts"),
  actionButtons: document.querySelectorAll(".action-button"),
  sidebarActions: document.querySelectorAll(".sidebar-action"),
  kpiButtons: document.querySelectorAll(".kpi-card"),
  navItems: document.querySelectorAll(".nav-item"),
};

document.addEventListener("DOMContentLoaded", () => {
  elements.refreshAll.addEventListener("click", () => loadAllData({ keepLead: true, keepWeek: true }));
  elements.weekSelect.addEventListener("change", handleWeekChange);
  elements.leadSearch.addEventListener("input", handleSearch);
  elements.focusFilter.addEventListener("change", handleFocusFilter);
  elements.conversionForm.addEventListener("submit", handleConversionSubmit);
  elements.convertClear.addEventListener("click", clearConversionSelection);
  elements.actionButtons.forEach((button) => {
    button.addEventListener("click", () => triggerAction(button.dataset.action));
  });
  elements.sidebarActions.forEach((button) => {
    button.addEventListener("click", () => triggerAction(button.dataset.action));
  });
  elements.navItems.forEach((button) => {
    button.addEventListener("click", () => navigateTo(button));
  });
  elements.kpiButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.focusFilter = button.dataset.focus || "all";
      elements.focusFilter.value = state.focusFilter;
      renderPipeline();
      renderFilterTags();
      renderKpiSelection();
      updateStatusMessage();
    });
  });

  loadAllData();
});

async function loadAllData(options = {}) {
  setFeedback("");
  setStatus("Carregando dados do pipeline, da prospecção e das conversões...");

  try {
    const [summary, leads, prospects] = await Promise.all([
      api("/leads/pipeline/summary"),
      api("/leads/"),
      api("/prospects/"),
    ]);

    state.summary = summary;
    state.leads = leads;
    state.prospects = prospects;
    state.weeks = deriveWeeks(prospects);
    state.selectedWeek = resolveSelectedWeek(options.keepWeek);
    state.lastUpdated = new Date();

    await loadWeeklyStats();
    renderWeekSelect();
    renderHeroStats();
    renderKpiSelection();
    renderExecutiveSummary();
    renderPipelineStrip();
    renderInsights();
    renderPipeline();
    renderWeeklyView();
    renderHistoryChart();
    renderProspects();
    renderActivityFeed();
    renderLastUpdated();
    renderFilterTags();

    if (options.keepLead && state.selectedLeadId && state.leads.some((lead) => lead.id === state.selectedLeadId)) {
      await selectLead(state.selectedLeadId);
    } else if (state.leads[0]) {
      await selectLead(state.leads[0].id);
    } else {
      renderLeadEmptyState("Nenhum lead encontrado no pipeline.");
    }

    updateStatusMessage();
  } catch (error) {
    renderGlobalError(error);
  }
}

function resolveSelectedWeek(keepWeek) {
  if (keepWeek && state.selectedWeek && state.weeks.includes(state.selectedWeek)) {
    return state.selectedWeek;
  }
  return state.weeks[state.weeks.length - 1] ?? null;
}

async function loadWeeklyStats() {
  state.weeklyStats.clear();
  await Promise.all(
    state.weeks.map(async (week) => {
      const stats = await api(`/prospects/week/stats?week=${encodeURIComponent(week)}`);
      state.weeklyStats.set(week, stats);
    }),
  );
}

function renderHeroStats() {
  const converted = state.prospects.filter((prospect) => prospect.status === "convertido").length;
  const interactions = state.leads.reduce((acc, lead) => acc + lead.interaction_count, 0);
  const activeLeads = state.leads.filter((lead) => !["cliente", "sem_momento"].includes(lead.stage)).length;
  const urgentLeads = getUrgentLeads().length;
  const currentStats = state.weeklyStats.get(state.selectedWeek);
  const priorStats = getPreviousWeekStats();

  elements.statLeads.textContent = formatInteger(activeLeads);
  elements.statInteractions.textContent = formatInteger(interactions);
  elements.statConverted.textContent = formatInteger(converted);
  elements.statFollowups.textContent = formatInteger(urgentLeads);

  elements.statLeadsDelta.textContent = `${formatInteger(state.leads.length)} no total • ${stageLabel(topStageByCount())} concentra mais volume`;
  elements.statFollowupsDelta.textContent = urgentLeads
    ? `${formatInteger(urgentLeads)} oportunidades pedem ação até amanhã`
    : "Nenhuma ação crítica na janela";
  elements.statInteractionsDelta.textContent = `${averageInteractions().toFixed(1).replace(".", ",")} interações por lead em média`;

  // Alerta = o que está fora do controle do operador: ação vencida ou lead
  // ativo sem próxima ação definida. Sai de contagem, não é número fixo.
  const overdue = getOverdueLeads().length;
  const noDate = getNoDateLeads().length;
  elements.statAlerts.textContent = formatInteger(overdue + noDate);
  elements.statAlerts.parentElement.title =
    `${overdue} ação(ões) vencida(s) · ${noDate} lead(s) ativo(s) sem próxima ação`;

  elements.statConvertedDelta.textContent = priorStats && currentStats
    ? compareConversion(currentStats.convertido, priorStats.convertido)
    : "Semana selecionada em leitura";
}

function renderKpiSelection() {
  elements.kpiButtons.forEach((button) => {
    button.classList.toggle("is-active", (button.dataset.focus || "all") === state.focusFilter);
  });
}

function renderExecutiveSummary() {
  const clientCount = state.summary.cliente ?? 0;
  const urgentCount = getUrgentLeads().length;
  const noDateCount = getNoDateLeads().length;
  const topStage = topStageByCount();
  const topStageCount = state.summary[topStage] ?? 0;

  elements.executiveSummary.textContent =
    `${stageLabel(topStage)} concentra ${formatInteger(topStageCount)} leads, enquanto ${formatInteger(urgentCount)} oportunidades exigem ação até amanhã e ${formatInteger(clientCount)} já estão em cliente.`;

  if (urgentCount >= 5) {
    elements.featureHeadline.textContent = "A operação está viva, mas há pressão de follow-up no topo do funil.";
    elements.featureText.textContent =
      `${formatInteger(urgentCount)} leads têm ação atrasada, para hoje ou para amanhã. O funil parece saudável no volume, mas o risco está em deixar novo contato e qualificação perderem cadência.`;
    elements.summaryTag.textContent = "Atenção";
    elements.summaryTag.className = "tag tag--bad";
  } else if (clientCount >= 3) {
    elements.featureHeadline.textContent = "O pipeline mostra progresso real do início ao fechamento.";
    elements.featureText.textContent =
      `${formatInteger(clientCount)} leads já chegaram a cliente, enquanto todas as 8 etapas seguem representadas. Isso ajuda o case a parecer operação comercial contínua, não cadastro vazio.`;
    elements.summaryTag.textContent = "Acima da meta";
    elements.summaryTag.className = "tag tag--good";
  } else {
    elements.featureHeadline.textContent = "O volume está distribuído, mas a atenção precisa ser calibrada por urgência.";
    elements.featureText.textContent =
      `${formatInteger(noDateCount)} leads ainda não têm próxima ação definida. O funil ocupa todas as etapas, mas a disciplina de acompanhamento segue sendo o ponto crítico da operação.`;
    elements.summaryTag.textContent = "Oportunidade";
    elements.summaryTag.className = "tag tag--warning";
  }
}

function renderPipelineStrip() {
  const max = Math.max(...Object.values(state.summary), 1);
  elements.pipelineStrip.innerHTML = STAGES.map(([key, label]) => {
    const value = state.summary[key] ?? 0;
    const height = Math.max(24, Math.round((value / max) * 140));
    return `
      <div class="axis-bar" title="${label}: ${value} leads">
        <span class="axis-bar__value">${value}</span>
        <div class="axis-bar__bar" style="height:${height}px"></div>
        <span class="axis-bar__label">${label}</span>
      </div>
    `;
  }).join("");
}

function renderInsights() {
  const urgentLeads = getUrgentLeads();
  const noDateLeads = getNoDateLeads();
  const weeklyStats = state.weeklyStats.get(state.selectedWeek);
  const priorStats = getPreviousWeekStats();
  const contactadosNoAlvo = weeklyStats ? weeklyStats.contactado + weeklyStats.convertido : 0;

  const insights = [
    {
      type: urgentLeads.length >= 5 ? "bad" : "warning",
      tag: urgentLeads.length >= 5 ? "Atenção" : "Monitorar",
      title: `${formatInteger(urgentLeads.length)} leads pedem ação imediata`,
      text: urgentLeads.length
        ? `A pressão está concentrada em ${summarizeLeadNames(urgentLeads)}. Vale priorizar retorno antes de abrir mais frentes.`
        : "Nenhuma oportunidade está vencida ou na janela crítica de amanhã.",
    },
    {
      type: contactadosNoAlvo >= (weeklyStats?.meta_contactadas ?? 10) ? "good" : "warning",
      tag: contactadosNoAlvo >= (weeklyStats?.meta_contactadas ?? 10) ? "Meta batida" : "Ajustar",
      title: weeklyStats
        ? `${contactadosNoAlvo}/${weeklyStats.meta_contactadas} contactados na semana selecionada`
        : "Leitura semanal indisponível",
      text: weeklyStats
        ? `A semana de ${formatDate(weeklyStats.week)} soma ${weeklyStats.total} prospects pesquisados e ${weeklyStats.convertido} convertidos em lead.`
        : "Sem dados suficientes para compor a leitura semanal.",
    },
    {
      type: noDateLeads.length ? "warning" : "good",
      tag: noDateLeads.length ? "Oportunidade" : "Coberto",
      title: `${formatInteger(noDateLeads.length)} leads sem próxima ação definida`,
      text: noDateLeads.length
        ? `Sem data, o CRM perde o poder de priorização. Hoje isso aparece sobretudo em ${summarizeLeadNames(noDateLeads)}.`
        : "Todos os leads ativos têm próxima ação registrada.",
    },
  ];

  if (priorStats && weeklyStats) {
    insights.push({
      type: weeklyStats.convertido >= priorStats.convertido ? "good" : "info",
      tag: "Comparação",
      title: compareConversion(weeklyStats.convertido, priorStats.convertido),
      text: `Na semana anterior houve ${priorStats.convertido} conversões. O comparativo ajuda a explicar se o volume atual é pico ou padrão.`,
    });
  }

  elements.insightList.innerHTML = insights
    .map(
      (item) => `
        <article class="insight-item">
          <span class="tag tag--${item.type}">${escapeHtml(item.tag)}</span>
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.text)}</p>
        </article>
      `,
    )
    .join("");
}

function renderPipeline() {
  const filteredLeads = getFilteredLeads();
  const leadsByStage = groupBy(filteredLeads, "stage");

  elements.board.innerHTML = "";
  elements.pipelineTotal.textContent = `${formatInteger(filteredLeads.length)} leads visíveis nas 8 etapas do funil`;

  STAGES.forEach(([stageKey, label, subtitle]) => {
    const stageLeads = (leadsByStage[stageKey] ?? []).slice().sort(sortLeadsByUrgency);
    const column = document.createElement("section");
    column.className = "pipeline-column";
    column.innerHTML = `
      <div class="pipeline-column__header">
        <div class="lead-card__head">
          <h3>${label}</h3>
          <span class="tag">${stageLeads.length}</span>
        </div>
        <p>${subtitle}</p>
      </div>
    `;

    const list = document.createElement("div");
    list.className = "column-list";

    if (!stageLeads.length) {
      list.innerHTML = '<div class="empty-list">Nenhum lead visível nesta etapa.</div>';
    } else {
      stageLeads.forEach((lead) => list.appendChild(createLeadCard(lead)));
    }

    column.appendChild(list);
    elements.board.appendChild(column);
  });
}

function createLeadCard(lead) {
  const fragment = elements.leadCardTemplate.content.cloneNode(true);
  const button = fragment.querySelector(".lead-card");

  if (lead.id === state.selectedLeadId) {
    button.classList.add("is-active");
  }

  fragment.querySelector(".lead-card__company").textContent = lead.company_name;
  fragment.querySelector(".lead-card__count").textContent = `${lead.interaction_count} interações`;
  fragment.querySelector(".lead-card__contact").textContent = lead.contact_name;
  fragment.querySelector(".lead-card__action").textContent = lead.next_action
    ? `${lead.next_action}${lead.next_action_date ? ` · ${formatDate(lead.next_action_date)}` : ""}`
    : "Sem próxima ação definida";
  fragment.querySelector(".lead-card__source").textContent = SOURCE_LABELS[lead.source] ?? lead.source;
  fragment.querySelector(".lead-card__date").textContent = describeUrgency(lead.next_action_date);

  button.addEventListener("click", () => selectLead(lead.id));
  return fragment;
}

async function selectLead(leadId) {
  state.selectedLeadId = leadId;
  renderPipeline();

  if (!state.leadDetails.has(leadId)) {
    try {
      const detail = await api(`/leads/${leadId}`);
      state.leadDetails.set(leadId, detail);
    } catch (error) {
      renderLeadEmptyState(extractErrorMessage(error));
      return;
    }
  }

  renderLeadDetail(state.leadDetails.get(leadId));
}

function renderLeadDetail(lead) {
  elements.leadDetail.className = "lead-detail";
  elements.leadDetailTitle.textContent = lead.company_name;
  elements.leadDetailStage.textContent = stageLabel(lead.stage);

  const interactions = lead.interactions.slice().sort((a, b) => b.date.localeCompare(a.date));
  const interactionItems = interactions.length
    ? interactions
        .map(
          (item) => `
            <article class="timeline-item">
              <div class="timeline-item__meta">${escapeHtml(INTERACTION_LABELS[item.type] ?? item.type)} · ${formatDate(item.date)}</div>
              <strong>${escapeHtml(item.description)}</strong>
            </article>
          `,
        )
        .join("")
    : '<div class="empty-list">Nenhuma interação registrada.</div>';

  const noteText = lead.notes || "Sem notas registradas para este lead.";
  const urgencyText = describeUrgency(lead.next_action_date);

  elements.leadDetail.innerHTML = `
    <div class="lead-detail__hero">
      <p class="panel__eyebrow">Contato principal</p>
      <strong>${escapeHtml(lead.contact_name)}</strong>
      <p>${escapeHtml(lead.email || "Sem e-mail")} · ${escapeHtml(lead.phone || "Sem telefone")}</p>
    </div>

    <div class="lead-meta-grid">
      <article class="lead-meta">
        <span>Origem</span>
        <strong>${escapeHtml(SOURCE_LABELS[lead.source] ?? lead.source)}</strong>
      </article>
      <article class="lead-meta">
        <span>Próxima ação</span>
        <strong>${escapeHtml(lead.next_action || "Não definida")}</strong>
        <p>${lead.next_action_date ? `${formatDate(lead.next_action_date)} • ${urgencyText}` : "Sem data"}</p>
      </article>
      <article class="lead-meta">
        <span>Interações</span>
        <strong>${interactions.length}</strong>
        <p>${interactions.length >= 4 ? "Histórico denso" : "Histórico em formação"}</p>
      </article>
      <article class="lead-meta">
        <span>Atualizado em</span>
        <strong>${formatDateTime(lead.updated_at)}</strong>
      </article>
    </div>

    <article class="lead-meta">
      <span>Leitura editorial</span>
      <strong>${escapeHtml(describeLeadNarrative(lead, interactions.length))}</strong>
      <p>${escapeHtml(noteText)}</p>
    </article>

    <div>
      <p class="panel__eyebrow">Histórico de interações</p>
      <div class="timeline">${interactionItems}</div>
    </div>
  `;
}

function renderLeadEmptyState(message) {
  elements.leadDetailTitle.textContent = "Selecione um lead";
  elements.leadDetailStage.textContent = "Pipeline";
  elements.leadDetail.className = "lead-detail empty-state";
  elements.leadDetail.textContent = message;
}

function renderWeekSelect() {
  elements.weekSelect.innerHTML = "";
  state.weeks.forEach((week) => {
    const option = document.createElement("option");
    option.value = week;
    option.textContent = weekLabel(week);
    option.selected = week === state.selectedWeek;
    elements.weekSelect.appendChild(option);
  });
}

function renderWeeklyView() {
  const stats = state.weeklyStats.get(state.selectedWeek);
  if (!stats) {
    elements.weeklyKpis.innerHTML = '<div class="empty-list">Sem métricas para esta semana.</div>';
    elements.weeklyBars.innerHTML = "";
    elements.selectedWeekLabel.textContent = "Sem período";
    return;
  }

  elements.selectedWeekLabel.textContent = weekLabel(stats.week);

  const contactadosNoAlvo = stats.contactado + stats.convertido;
  const kpis = [
    ["Prospects pesquisados", `${stats.total}/${stats.meta_pesquisadas}`],
    ["Prospects contactados", `${contactadosNoAlvo}/${stats.meta_contactadas}`],
    ["Convertidos em lead", formatInteger(stats.convertido)],
    ["Descartados", formatInteger(stats.descartado)],
  ];

  elements.weeklyKpis.innerHTML = kpis
    .map(
      ([label, value]) => `
        <article class="weekly-kpi">
          <span>${label}</span>
          <strong>${value}</strong>
        </article>
      `,
    )
    .join("");

  const barRows = [
    [
      "Pesquisados",
      stats.total,
      stats.meta_pesquisadas,
      "",
      stats.total >= stats.meta_pesquisadas ? "Acima da meta" : "Abaixo da meta",
    ],
    [
      "Contactados",
      contactadosNoAlvo,
      stats.meta_contactadas,
      " bar-fill--warm",
      contactadosNoAlvo >= stats.meta_contactadas ? "Meta batida" : "Ajustar cadência",
    ],
    ["Qualificados", stats.qualificado, stats.meta_pesquisadas, "", "Estoques para próxima conversão"],
    ["Convertidos", stats.convertido, stats.meta_contactadas, " bar-fill--warm", "Integração prospect → lead"],
  ];

  elements.weeklyBars.innerHTML = barRows
    .map(([label, value, meta, modifier, note]) => {
      const width = meta ? Math.min((value / meta) * 100, 100) : 0;
      return `
        <div class="bar-row">
          <div class="bar-row__labels">
            <span>${label}</span>
            <span>${value} / ${meta}</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill${modifier}" style="width:${width}%"></div>
          </div>
          <div class="bar-row__labels">
            <span>${note}</span>
            <span>${Math.round(width)}%</span>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderHistoryChart() {
  elements.historyChart.innerHTML = state.weeks
    .map((week) => {
      const stats = state.weeklyStats.get(week);
      if (!stats) return "";

      const researchedWidth = Math.min((stats.total / stats.meta_pesquisadas) * 100, 100);
      const contactedValue = stats.contactado + stats.convertido;
      const contactedWidth = Math.min((contactedValue / stats.meta_contactadas) * 100, 100);

      return `
        <article class="history-week">
          <div class="history-week__header">
            <strong>${weekLabel(week)}</strong>
            <span>${stats.convertido} convertidos</span>
          </div>
          <div class="history-week__bars">
            <div>
              <div class="bar-row__labels">
                <span>Pesquisados</span>
                <span>${stats.total}/${stats.meta_pesquisadas}</span>
              </div>
              <div class="history-track">
                <span class="researched" style="width:${researchedWidth}%"></span>
              </div>
            </div>
            <div>
              <div class="bar-row__labels">
                <span>Contactados</span>
                <span>${contactedValue}/${stats.meta_contactadas}</span>
              </div>
              <div class="history-track">
                <span class="contacted" style="width:${contactedWidth}%"></span>
              </div>
            </div>
          </div>
          <p>${historyAnnotation(stats)}</p>
        </article>
      `;
    })
    .join("");
}

function renderProspects() {
  const prospects = eligibleProspects()
    .sort((a, b) => {
      const statusScore = { contactado: 0, qualificado: 1, pesquisando: 2 };
      return (
        (statusScore[a.status] ?? 9) - (statusScore[b.status] ?? 9) ||
        a.company_name.localeCompare(b.company_name)
      );
    })
    .slice(0, 12);

  elements.conversionCount.textContent = `${prospects.length} prospects elegíveis na semana selecionada`;

  if (!prospects.length) {
    elements.prospectList.innerHTML = '<div class="empty-list">Nenhum prospect elegível nesta semana.</div>';
    clearConversionSelection();
    return;
  }

  elements.prospectList.innerHTML = "";
  prospects.forEach((prospect) => {
    const item = document.createElement("article");
    item.className = "prospect-item";
    item.innerHTML = `
      <div class="prospect-item__top">
        <strong>${escapeHtml(prospect.company_name)}</strong>
        <span class="tag ${prospect.status === "contactado" ? "tag--warning" : "tag--good"}">
          ${escapeHtml(STATUS_LABELS[prospect.status] ?? prospect.status)}
        </span>
      </div>
      <div class="prospect-item__meta">
        <span>${escapeHtml(SEGMENT_LABELS[prospect.segment] ?? prospect.segment)}</span>
        <span>${escapeHtml(PROSPECT_SOURCE_LABELS[prospect.source] ?? prospect.source)}</span>
        <span>${escapeHtml(prospect.contact_name || "Sem contato salvo")}</span>
      </div>
      <p>${escapeHtml(prospect.signals || prospect.notes || "Sem sinais anotados.")}</p>
      <div class="form-actions">
        <button class="primary-button" type="button">Preparar conversão</button>
        <button class="ghost-button" type="button" disabled>
          ${prospect.status === "contactado" ? "Contato já feito" : "Em pesquisa"}
        </button>
      </div>
    `;

    const prepareButton = item.querySelector(".primary-button");
    prepareButton.addEventListener("click", () => selectProspect(prospect.id));
    elements.prospectList.appendChild(item);
  });

  if (state.selectedProspectId && !prospects.some((prospect) => prospect.id === state.selectedProspectId)) {
    clearConversionSelection();
  }
}

function renderActivityFeed() {
  const weeklyStats = state.weeklyStats.get(state.selectedWeek);
  const urgentLeads = getUrgentLeads().slice(0, 3);
  const activeLeads = getFilteredLeads().slice(0, 3);
  const items = [];

  if (weeklyStats) {
    items.push({
      title: `Semana de ${formatDate(weeklyStats.week)} consolidada`,
      meta: `${weeklyStats.total} prospects pesquisados`,
      text: `${weeklyStats.convertido} conversões já viraram lead e ${weeklyStats.descartado} foram descartados com motivo.`,
    });
  }

  urgentLeads.forEach((lead) => {
    items.push({
      title: `${lead.company_name} precisa de retorno`,
      meta: `${stageLabel(lead.stage)} • ${describeUrgency(lead.next_action_date)}`,
      text: lead.next_action || "Sem próxima ação detalhada.",
    });
  });

  activeLeads.forEach((lead) => {
    if (urgentLeads.some((item) => item.id === lead.id)) return;
    items.push({
      title: `${lead.company_name} segue no fluxo`,
      meta: `${stageLabel(lead.stage)} • ${lead.interaction_count} interações`,
      text: lead.next_action ? `Próxima ação: ${lead.next_action}.` : "Lead ainda sem próxima ação definida.",
    });
  });

  elements.activityFeed.innerHTML = items
    .slice(0, 6)
    .map(
      (item) => `
        <article class="activity-item">
          <div class="activity-item__meta">
            <strong>${escapeHtml(item.title)}</strong>
            <span>${escapeHtml(item.meta)}</span>
          </div>
          <p>${escapeHtml(item.text)}</p>
        </article>
      `,
    )
    .join("");
}

function handleWeekChange(event) {
  state.selectedWeek = event.target.value;
  renderHeroStats();
  renderExecutiveSummary();
  renderInsights();
  renderWeeklyView();
  renderHistoryChart();
  renderProspects();
  renderActivityFeed();
  renderLastUpdated();
  updateStatusMessage();
}

function handleSearch(event) {
  state.search = event.target.value.trim().toLowerCase();
  renderPipeline();
  renderFilterTags();
  updateStatusMessage();
}

function handleFocusFilter(event) {
  state.focusFilter = event.target.value;
  renderPipeline();
  renderFilterTags();
  updateStatusMessage();
}

function renderFilterTags() {
  const tags = [];

  if (state.search) {
    tags.push(`<span class="tag tag--info">Busca: ${escapeHtml(state.search)}</span>`);
  }

  if (state.focusFilter !== "all") {
    tags.push(`<span class="tag tag--warning">${FOCUS_LABELS[state.focusFilter]}</span>`);
  }

  elements.activeFilters.innerHTML = tags.length ? tags.join("") : '<span class="tag">Sem filtros ativos</span>';
}

function navigateTo(button) {
  const alvo = document.getElementById(button.dataset.target || "");
  if (!alvo) {
    return;
  }

  elements.navItems.forEach((item) => item.classList.toggle("is-active", item === button));
  alvo.scrollIntoView({ behavior: "smooth", block: "start" });
  setStatus(`Área em foco: ${button.textContent.trim()}.`);
}

function triggerAction(action) {
  const messages = {
    exportar: "Exportação simulada preparada. Em um produto real, esta ação geraria CSV ou PDF.",
    investigar: "Modo de investigação acionado: use o pipeline, os insights e o detalhe do lead para abrir o gargalo.",
    comparar: "Comparação entre semanas destacada pela cadência de prospecção e pelas conversões semanais.",
    relatorio: "Relatório contextual: use o detalhe do lead e a coluna de insights como resumo executivo.",
  };

  setStatus(messages[action] || "Ação contextual disparada.");
}

async function handleConversionSubmit(event) {
  event.preventDefault();
  if (!state.selectedProspectId) return;

  const payload = {
    contact_name: elements.convertContactName.value.trim(),
    phone: optionalField(elements.convertPhone.value),
    email: optionalField(elements.convertEmail.value),
    notes: optionalField(elements.convertNotes.value),
  };

  if (!payload.contact_name) {
    setFeedback("Informe o nome do contato para converter o prospect.", true);
    return;
  }

  elements.convertSubmit.disabled = true;
  setFeedback("Convertendo prospect...");

  try {
    const converted = await api(`/prospects/${state.selectedProspectId}/convert`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    setFeedback(
      `Prospect convertido com sucesso. Lead #${converted.lead_id} entrou em Qualificando.`,
      false,
      true,
    );
    clearLeadCache();
    resetConversionFields();
    await loadAllData({ keepLead: false, keepWeek: true });
    if (converted.lead_id) {
      await selectLead(converted.lead_id);
    }
  } catch (error) {
    elements.convertSubmit.disabled = false;
    setFeedback(extractErrorMessage(error), true);
  }
}

function selectProspect(prospectId) {
  const prospect = state.prospects.find((item) => item.id === prospectId);
  if (!prospect) return;

  state.selectedProspectId = prospectId;
  elements.convertCompany.value = prospect.company_name;
  elements.convertContactName.value = prospect.contact_name || "";
  elements.convertPhone.value = prospect.phone || "";
  elements.convertEmail.value = prospect.email || "";
  elements.convertNotes.value = prospect.signals || prospect.notes || "";
  elements.convertSubmit.disabled = false;
  setFeedback(`Prospect ${prospect.company_name} pronto para conversão.`);
  setStatus(`Prospect ${prospect.company_name} preparado para virar lead.`);
}

function clearConversionSelection() {
  state.selectedProspectId = null;
  resetConversionFields();
  setFeedback("");
}

function resetConversionFields() {
  elements.convertCompany.value = "";
  elements.convertContactName.value = "";
  elements.convertPhone.value = "";
  elements.convertEmail.value = "";
  elements.convertNotes.value = "";
  elements.convertSubmit.disabled = true;
}

function renderLastUpdated() {
  elements.lastUpdated.textContent = `Atualizado ${relativeTime(state.lastUpdated)}`;
}

function updateStatusMessage() {
  const filtered = getFilteredLeads().length;
  const urgent = getUrgentLeads().length;
  const currentWeek = state.weeklyStats.get(state.selectedWeek);

  if (!currentWeek) {
    setStatus(`Mostrando ${formatInteger(filtered)} leads visíveis no pipeline.`);
    return;
  }

  setStatus(
    `Mostrando ${formatInteger(filtered)} leads visíveis, ${formatInteger(urgent)} em janela crítica e ${formatInteger(currentWeek.convertido)} conversões na semana de ${formatDate(currentWeek.week)}.`,
  );
}

function getFilteredLeads() {
  return state.leads.filter((lead) => {
    const matchesSearch =
      !state.search ||
      `${lead.company_name} ${lead.contact_name}`.toLowerCase().includes(state.search);

    if (!matchesSearch) return false;

    switch (state.focusFilter) {
      case "urgent":
        return isUrgentLead(lead);
      case "rich":
        return lead.interaction_count >= 4;
      case "converted":
        return lead.source === "prospeccao_ativa";
      case "no_date":
        return !lead.next_action_date;
      default:
        return true;
    }
  });
}

function getUrgentLeads() {
  return state.leads.filter(isUrgentLead);
}

function getNoDateLeads() {
  return state.leads.filter(
    (lead) => !lead.next_action_date && !["cliente", "sem_momento"].includes(lead.stage),
  );
}

function getOverdueLeads() {
  return state.leads.filter(
    (lead) =>
      lead.next_action_date &&
      !["cliente", "sem_momento"].includes(lead.stage) &&
      dateDiffInDays(lead.next_action_date) < 0,
  );
}

function isUrgentLead(lead) {
  if (!lead.next_action_date) return false;
  if (["cliente", "sem_momento"].includes(lead.stage)) return false;
  return dateDiffInDays(lead.next_action_date) <= 1;
}

function averageInteractions() {
  if (!state.leads.length) return 0;
  return state.leads.reduce((acc, lead) => acc + lead.interaction_count, 0) / state.leads.length;
}

function topStageByCount() {
  return STAGES.reduce((winner, [stageKey]) => {
    const current = state.summary[stageKey] ?? 0;
    const best = state.summary[winner] ?? -1;
    return current > best ? stageKey : winner;
  }, STAGES[0][0]);
}

function getPreviousWeekStats() {
  const currentIndex = state.weeks.indexOf(state.selectedWeek);
  if (currentIndex <= 0) return null;
  return state.weeklyStats.get(state.weeks[currentIndex - 1]) ?? null;
}

function compareConversion(current, previous) {
  if (current === previous) {
    return `${current} conversões, estável vs. semana anterior`;
  }
  if (current > previous) {
    return `${current} conversões, alta de ${current - previous} vs. semana anterior`;
  }
  return `${current} conversões, queda de ${previous - current} vs. semana anterior`;
}

function historyAnnotation(stats) {
  const contactedValue = stats.contactado + stats.convertido;
  if (stats.convertido >= 3) {
    return "Semana forte: a meta foi cumprida e o volume convertido já alimenta o CRM sem recadastro.";
  }
  if (contactedValue >= stats.meta_contactadas) {
    return "Cadência preservada: a semana bateu a meta de contatos, mas converteu abaixo do pico.";
  }
  return "Semana abaixo do ritmo planejado, exigindo reforço de abordagem ou segmentação.";
}

function describeLeadNarrative(lead, interactionCount) {
  if (lead.stage === "cliente") {
    return "Lead fechado, com histórico suficiente para sustentar prova de competência.";
  }
  if (lead.stage === "negociacao" || lead.stage === "proposta_enviada") {
    return "Oportunidade madura, já em fase de decisão ou ajuste comercial.";
  }
  if (interactionCount >= 4) {
    return "Lead em desenvolvimento, com histórico claro de avanço pelo funil.";
  }
  return "Lead ainda no começo do processo, com espaço para aprofundar contexto e urgência.";
}

function summarizeLeadNames(leads) {
  const names = leads.slice(0, 2).map((lead) => lead.company_name);
  if (leads.length === 1) return names[0];
  if (leads.length === 2) return `${names[0]} e ${names[1]}`;
  return `${names[0]}, ${names[1]} e mais ${leads.length - 2}`;
}

function sortLeadsByUrgency(a, b) {
  const diffA = urgencyScore(a.next_action_date);
  const diffB = urgencyScore(b.next_action_date);
  return diffA - diffB || a.company_name.localeCompare(b.company_name);
}

function urgencyScore(dateValue) {
  if (!dateValue) return Number.MAX_SAFE_INTEGER;
  return dateDiffInDays(dateValue);
}

function describeUrgency(dateValue) {
  if (!dateValue) return "Sem data";
  const diff = dateDiffInDays(dateValue);
  if (diff < 0) return `${Math.abs(diff)}d atrasado`;
  if (diff === 0) return "Hoje";
  if (diff === 1) return "Amanhã";
  return `${diff}d`;
}

function dateDiffInDays(dateValue) {
  const target = new Date(`${dateValue}T12:00:00`);
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  return Math.round((target - today) / 86400000);
}

function eligibleProspects() {
  return state.prospects.filter((prospect) => {
    const isSelectedWeek = prospect.week === state.selectedWeek;
    const isEligible = ["pesquisando", "qualificado", "contactado"].includes(prospect.status);
    return isSelectedWeek && isEligible;
  });
}

function renderGlobalError(error) {
  const message = extractErrorMessage(error);
  elements.board.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
  elements.prospectList.innerHTML = "";
  renderLeadEmptyState(message);
  setStatus(message);
}

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = "Falha ao carregar dados da API.";
    try {
      const data = await response.json();
      detail = data.detail || data.message || detail;
    } catch (_error) {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function groupBy(items, key) {
  return items.reduce((groups, item) => {
    const value = item[key];
    groups[value] = groups[value] || [];
    groups[value].push(item);
    return groups;
  }, {});
}

function deriveWeeks(prospects) {
  return Array.from(new Set(prospects.map((prospect) => prospect.week).filter(Boolean))).sort();
}

function stageLabel(stage) {
  const match = STAGES.find(([key]) => key === stage);
  return match ? match[1] : stage;
}

function formatDate(value) {
  if (!value) return "Sem data";
  return new Date(`${value}T12:00:00`).toLocaleDateString("pt-BR");
}

function formatDateTime(value) {
  if (!value) return "Sem data";
  return new Date(value).toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function weekLabel(week) {
  const date = new Date(`${week}T12:00:00`);
  return `Semana de ${date.toLocaleDateString("pt-BR")}`;
}

function formatInteger(value) {
  return new Intl.NumberFormat("pt-BR").format(value);
}

function optionalField(value) {
  const trimmed = value.trim();
  return trimmed || null;
}

function relativeTime(date) {
  if (!date) return "agora";
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.max(0, Math.round(diffMs / 60000));
  if (diffMin === 0) return "agora";
  if (diffMin === 1) return "há 1 minuto";
  return `há ${diffMin} minutos`;
}

function setFeedback(message, isError = false, isSuccess = false) {
  elements.conversionFeedback.textContent = message;
  elements.conversionFeedback.classList.toggle("is-error", isError);
  elements.conversionFeedback.classList.toggle("is-success", isSuccess);
}

function setStatus(message) {
  elements.dashboardStatus.textContent = message;
}

function clearLeadCache() {
  state.leadDetails.clear();
  state.selectedLeadId = null;
}

function extractErrorMessage(error) {
  return error instanceof Error ? error.message : "Erro inesperado.";
}

/**
 * Escapa texto que vai para `innerHTML`.
 *
 * Nome de empresa, contato, notas e sinais são campos livres da API: sem isto,
 * uma empresa chamada "Auto Peças <Vinhedo>" quebra a renderização, e um campo
 * com `<img src=x onerror=...>` executa script na página. Aceita nulo porque
 * quase todo campo de texto da API é opcional.
 */
function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
