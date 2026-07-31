/* =========================================================
   LeadDesk — camada de interface

   Os gráficos são SVG escrito à mão: o projeto é servido como
   estático pela própria API, sem passo de build, então uma
   biblioteca de charts significaria um bundler. Três formas
   simples não justificam isso.

   Regras de cor: ver o cabeçalho de styles.css. Aqui só se
   consomem as variáveis por papel (--s1, --s2), nunca hex solto.
   ========================================================= */

const STAGES = [
  ["novo_contato", "Novo contato"],
  ["qualificando", "Qualificando"],
  ["reuniao_agendada", "Reunião agendada"],
  ["proposta_enviada", "Proposta enviada"],
  ["negociacao", "Negociação"],
  ["cliente", "Cliente"],
  ["acompanhamento", "Acompanhamento"],
  ["sem_momento", "Sem momento"],
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

const SERIES = {
  s1: "var(--s1)",
  s2: "var(--s2)",
  s3: "var(--s3)",
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
};

const el = {};

document.addEventListener("DOMContentLoaded", () => {
  Object.assign(el, {
    board: q("#pipeline-board"),
    pipelineTotal: q("#pipeline-total"),
    refreshAll: q("#refresh-all"),
    leadDetail: q("#lead-detail"),
    weekSelect: q("#week-select"),
    leadSearch: q("#lead-search"),
    focusFilter: q("#focus-filter"),
    prospectList: q("#prospect-list"),
    conversionCount: q("#conversion-count"),
    conversionForm: q("#conversion-form"),
    convertCompany: q("#convert-company"),
    convertContactName: q("#convert-contact-name"),
    convertPhone: q("#convert-phone"),
    convertEmail: q("#convert-email"),
    convertNotes: q("#convert-notes"),
    convertSubmit: q("#convert-submit"),
    convertClear: q("#convert-clear"),
    conversionFeedback: q("#conversion-feedback"),
    activityFeed: q("#activity-feed"),
    dashboardStatus: q("#dashboard-status"),
    tooltip: q("#tooltip"),
    kpis: document.querySelectorAll(".kpi"),
    tableToggles: document.querySelectorAll(".table-toggle"),
  });

  el.refreshAll.addEventListener("click", () => loadAllData({ keepLead: true, keepWeek: true }));
  el.weekSelect.addEventListener("change", (event) => {
    state.selectedWeek = event.target.value;
    renderWeekChart();
    renderProspects();
    updateStatus();
  });
  el.leadSearch.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    renderPipeline();
    updateStatus();
  });
  el.focusFilter.addEventListener("change", (event) => {
    state.focusFilter = event.target.value;
    renderPipeline();
    renderKpiSelection();
    updateStatus();
  });
  el.conversionForm.addEventListener("submit", handleConversionSubmit);
  el.convertClear.addEventListener("click", clearConversionSelection);

  el.kpis.forEach((button) => {
    button.addEventListener("click", () => {
      const focus = button.dataset.focus || "all";
      state.focusFilter = state.focusFilter === focus ? "all" : focus;
      el.focusFilter.value = state.focusFilter;
      renderPipeline();
      renderKpiSelection();
      updateStatus();
    });
  });

  el.tableToggles.forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.table);
      const willShow = target.hidden;
      target.hidden = !willShow;
      button.setAttribute("aria-expanded", String(willShow));
      button.textContent = willShow ? "Ocultar tabela" : "Ver como tabela";
    });
  });

  window.addEventListener("resize", debounce(redrawCharts, 180));

  loadAllData();
});

/* =========================================================
   DADOS
   ========================================================= */

async function loadAllData(options = {}) {
  setFeedback("");
  setStatus("Carregando pipeline, prospecção e conversões.");

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

    await loadWeeklyStats();

    renderWeekSelect();
    renderKpis();
    renderKpiSelection();
    renderStageChart();
    renderWeekChart();
    renderHistoryChart();
    renderPipeline();
    renderProspects();
    renderActivityFeed();

    if (options.keepLead && state.selectedLeadId && state.leads.some((l) => l.id === state.selectedLeadId)) {
      await selectLead(state.selectedLeadId);
    } else if (state.leads[0]) {
      await selectLead(state.leads[0].id);
    } else {
      el.leadDetail.innerHTML = `<p class="empty">Nenhum lead no pipeline.</p>`;
    }

    updateStatus();
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
      state.weeklyStats.set(week, await api(`/prospects/week/stats?week=${encodeURIComponent(week)}`));
    }),
  );
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

/* =========================================================
   SVG — utilitários
   ========================================================= */

const NS = "http://www.w3.org/2000/svg";

function svgEl(name, attrs = {}) {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined) node.setAttribute(key, value);
  }
  return node;
}

/**
 * Escala do eixo com passo inteiro da família 1, 2, 5 × 10^n.
 *
 * Dividir o máximo por um número fixo de marcas e arredondar produz rótulos
 * irregulares — com máximo 5 e 4 marcas sai "0, 1, 3, 4, 5". Aqui o passo vem
 * primeiro e o topo é derivado dele, então os rótulos são sempre
 * equidistantes e inteiros.
 */
function niceScale(value, targetTicks = 4) {
  const safe = Math.max(1, value);
  const raw = safe / targetTicks;
  const base = 10 ** Math.floor(Math.log10(raw));
  const normalized = raw / base;
  const step = (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * base;
  const max = Math.ceil(safe / step) * step;
  const ticks = [];
  for (let tick = 0; tick <= max + 1e-9; tick += step) ticks.push(Math.round(tick));
  return { max, ticks };
}

/**
 * Retângulo com as duas pontas do lado do valor arredondadas e a base
 * quadrada, ancorada na linha de base. `d` é montado à mão porque o
 * `rx` do SVG arredonda os quatro cantos.
 */
function barPath(x, y, width, height, radius, horizontal) {
  const r = Math.max(0, Math.min(radius, horizontal ? width : height));
  if (horizontal) {
    return `M${x},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + height - r} Q${x + width},${y + height} ${x + width - r},${y + height} H${x} Z`;
  }
  return `M${x},${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + height} H${x} Z`;
}

/* =========================================================
   TOOLTIP
   ========================================================= */

function showTooltip(event, title, rows) {
  const body = rows
    .map(
      (row) => `<div class="tooltip__row">
          ${row.color ? `<span class="tooltip__swatch" style="background:${row.color}"></span>` : ""}
          <span>${escapeHtml(row.label)}</span>
          <span class="tooltip__value">${escapeHtml(row.value)}</span>
        </div>`,
    )
    .join("");

  el.tooltip.innerHTML = `<div class="tooltip__title">${escapeHtml(title)}</div>${body}`;
  el.tooltip.dataset.visible = "true";
  el.tooltip.setAttribute("aria-hidden", "false");
  moveTooltip(event);
}

function moveTooltip(event) {
  const pad = 14;
  const rect = el.tooltip.getBoundingClientRect();
  let x = event.clientX + pad;
  let y = event.clientY + pad;
  if (x + rect.width > window.innerWidth - 8) x = event.clientX - rect.width - pad;
  if (y + rect.height > window.innerHeight - 8) y = event.clientY - rect.height - pad;
  el.tooltip.style.left = `${Math.max(8, x)}px`;
  el.tooltip.style.top = `${Math.max(8, y)}px`;
}

function hideTooltip() {
  el.tooltip.dataset.visible = "false";
  el.tooltip.setAttribute("aria-hidden", "true");
}

/** Liga hover/foco de uma marca ao tooltip, com alvo maior que a marca. */
function bindHover(hit, mark, title, rows) {
  hit.addEventListener("mouseenter", (event) => {
    mark.classList.add("chart__mark--active");
    showTooltip(event, title, rows);
  });
  hit.addEventListener("mousemove", moveTooltip);
  hit.addEventListener("mouseleave", () => {
    mark.classList.remove("chart__mark--active");
    hideTooltip();
  });
}

/* =========================================================
   GRÁFICO 1 — Leads por etapa (barras horizontais, 1 série)
   ========================================================= */

function renderStageChart() {
  const host = q("#stage-chart");
  const data = STAGES.map(([key, label]) => ({ label, value: state.summary[key] ?? 0 })).filter(
    (row) => row.value > 0,
  );

  q("#stage-chart-meta").textContent = `${formatInteger(state.leads.length)} leads no funil`;

  if (!data.length) {
    host.innerHTML = `<p class="chart-empty">Nenhum lead no pipeline.</p>`;
    q("#stage-table").innerHTML = "";
    return;
  }

  const labelWidth = 128;
  const rowHeight = 30;
  const gap = 8;
  const padRight = 44;
  const width = host.clientWidth || 380;
  const height = data.length * rowHeight + (data.length - 1) * gap + 24;
  const plotWidth = Math.max(40, width - labelWidth - padRight);
  const { max, ticks } = niceScale(Math.max(...data.map((row) => row.value)));

  const svg = svgEl("svg", {
    class: "chart",
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": `Leads por etapa. ${data.map((r) => `${r.label}: ${r.value}`).join(". ")}.`,
  });

  // grade recessiva atrás das marcas
  ticks.forEach((tick) => {
    const x = labelWidth + (tick / max) * plotWidth;
    svg.append(
      svgEl("line", { class: "chart__grid", x1: x, y1: 0, x2: x, y2: height - 22 }),
      Object.assign(svgEl("text", { class: "chart__tick", x, y: height - 6, "text-anchor": "middle" }), {
        textContent: tick,
      }),
    );
  });

  data.forEach((row, index) => {
    const y = index * (rowHeight + gap);
    const barWidth = Math.max(2, (row.value / max) * plotWidth);

    svg.append(
      Object.assign(
        svgEl("text", { x: labelWidth - 10, y: y + rowHeight / 2 + 4, "text-anchor": "end" }),
        { textContent: row.label },
      ),
    );

    const mark = svgEl("path", {
      class: "chart__mark",
      d: barPath(labelWidth, y, barWidth, rowHeight, 4, true),
      fill: SERIES.s1,
    });
    svg.append(mark);

    // rótulo direto: dispensa consultar a grade para ler o valor
    svg.append(
      Object.assign(
        svgEl("text", {
          class: "chart__value",
          x: labelWidth + barWidth + 8,
          y: y + rowHeight / 2 + 4,
        }),
        { textContent: row.value },
      ),
    );

    const hit = svgEl("rect", {
      class: "chart__hit",
      x: labelWidth,
      y: y - gap / 2,
      width: plotWidth + padRight,
      height: rowHeight + gap,
    });
    svg.append(hit);
    bindHover(hit, mark, row.label, [
      { label: "Leads", value: formatInteger(row.value), color: "var(--s1)" },
    ]);
  });

  host.replaceChildren(svg);
  q("#stage-table").innerHTML = buildTable(["Etapa", "Leads"], data.map((r) => [r.label, r.value]));
}

/* =========================================================
   GRÁFICO 2 — Prospecção na semana (2 séries agrupadas)
   ========================================================= */

function renderWeekChart() {
  const host = q("#week-chart");
  const stats = state.weeklyStats.get(state.selectedWeek);

  if (!stats) {
    host.innerHTML = `<p class="chart-empty">Sem dados para a semana selecionada.</p>`;
    q("#week-chart-meta").textContent = "--";
    q("#week-table").innerHTML = "";
    return;
  }

  q("#week-chart-meta").textContent = weekLabel(stats.week);

  const groups = [
    { label: "Pesquisados", real: stats.pesquisando + stats.qualificado + stats.contactado + stats.convertido, meta: stats.meta_pesquisadas },
    { label: "Contactados", real: stats.contactado + stats.convertido, meta: stats.meta_contactadas },
    { label: "Convertidos", real: stats.convertido, meta: null },
  ];

  const width = host.clientWidth || 380;
  const height = 210;
  const padLeft = 34;
  const padBottom = 34;
  const plotHeight = height - padBottom - 12;
  const plotWidth = width - padLeft - 8;
  const { max, ticks } = niceScale(Math.max(1, ...groups.flatMap((g) => [g.real, g.meta ?? 0])));

  const svg = svgEl("svg", {
    class: "chart",
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": `Prospecção na semana. ${groups.map((g) => `${g.label}: ${g.real}${g.meta ? ` de meta ${g.meta}` : ""}`).join(". ")}.`,
  });

  ticks.forEach((tick) => {
    const y = 12 + plotHeight - (tick / max) * plotHeight;
    svg.append(
      svgEl("line", { class: "chart__grid", x1: padLeft, y1: y, x2: width - 8, y2: y }),
      Object.assign(svgEl("text", { class: "chart__tick", x: padLeft - 8, y: y + 4, "text-anchor": "end" }), {
        textContent: tick,
      }),
    );
  });

  const groupWidth = plotWidth / groups.length;
  const barWidth = Math.min(30, groupWidth / 3);

  groups.forEach((group, index) => {
    const center = padLeft + groupWidth * index + groupWidth / 2;
    const bars = group.meta === null
      ? [{ value: group.real, color: SERIES.s1, name: "Realizado" }]
      : [
          { value: group.real, color: SERIES.s1, name: "Realizado" },
          { value: group.meta, color: SERIES.s3, name: "Meta" },
        ];

    // 2px de respiro entre barras vizinhas: a superfície separa as marcas
    const totalWidth = bars.length * barWidth + (bars.length - 1) * 2;
    let x = center - totalWidth / 2;

    bars.forEach((bar) => {
      const barHeight = Math.max(2, (bar.value / max) * plotHeight);
      const y = 12 + plotHeight - barHeight;
      const mark = svgEl("path", {
        class: "chart__mark",
        d: barPath(x, y, barWidth, barHeight, 4, false),
        fill: bar.color,
      });
      svg.append(mark);

      const hit = svgEl("rect", {
        class: "chart__hit",
        x: x - 3,
        y: 12,
        width: barWidth + 6,
        height: plotHeight,
      });
      svg.append(hit);
      bindHover(hit, mark, group.label, [
        { label: bar.name, value: formatInteger(bar.value), color: bar.color },
      ]);

      x += barWidth + 2;
    });

    svg.append(
      Object.assign(
        svgEl("text", { x: center, y: height - 12, "text-anchor": "middle" }),
        { textContent: group.label },
      ),
    );
  });

  svg.append(
    svgEl("line", { class: "chart__axis", x1: padLeft, y1: 12 + plotHeight, x2: width - 8, y2: 12 + plotHeight }),
  );

  host.replaceChildren(legendFor([
    { label: "Realizado", color: "var(--s1)" },
    { label: "Meta", color: "var(--s3)" },
  ]), svg);

  q("#week-table").innerHTML = buildTable(
    ["Indicador", "Realizado", "Meta"],
    groups.map((g) => [g.label, g.real, g.meta ?? "—"]),
  );
}

/* =========================================================
   GRÁFICO 3 — Seis semanas (linhas, 2 séries)
   ========================================================= */

function renderHistoryChart() {
  const host = q("#history-chart");
  const weeks = state.weeks.slice(-6);
  const rows = weeks.map((week) => state.weeklyStats.get(week)).filter(Boolean);

  q("#history-chart-meta").textContent = `${rows.length} semanas`;

  if (rows.length < 2) {
    host.innerHTML = `<p class="chart-empty">São necessárias ao menos duas semanas para desenhar a série.</p>`;
    q("#history-table").innerHTML = "";
    return;
  }

  // Contactados não entra aqui: `contactado + convertido` é fixo na meta
  // semanal, então a série sairia numa reta e não diria nada. Convertidos e
  // descartados são o par que se move — e em direções opostas.
  const series = [
    { name: "Convertidos", color: SERIES.s1, get: (r) => r.convertido },
    { name: "Descartados", color: SERIES.s2, get: (r) => r.descartado },
  ];

  const width = host.clientWidth || 380;
  const height = 210;
  const padLeft = 34;
  const padBottom = 34;
  const plotHeight = height - padBottom - 12;
  const plotWidth = width - padLeft - 12;
  const { max, ticks } = niceScale(Math.max(1, ...rows.flatMap((r) => series.map((s) => s.get(r)))));
  const stepX = plotWidth / Math.max(1, rows.length - 1);
  const xAt = (i) => padLeft + i * stepX;
  const yAt = (v) => 12 + plotHeight - (v / max) * plotHeight;

  const svg = svgEl("svg", {
    class: "chart",
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": `Convertidos e descartados nas últimas ${rows.length} semanas.`,
  });

  ticks.forEach((tick) => {
    const y = yAt(tick);
    svg.append(
      svgEl("line", { class: "chart__grid", x1: padLeft, y1: y, x2: width - 12, y2: y }),
      Object.assign(svgEl("text", { class: "chart__tick", x: padLeft - 8, y: y + 4, "text-anchor": "end" }), {
        textContent: tick,
      }),
    );
  });

  series.forEach((serie) => {
    const d = rows.map((row, i) => `${i ? "L" : "M"}${xAt(i)},${yAt(serie.get(row))}`).join(" ");
    svg.append(
      svgEl("path", { d, fill: "none", stroke: serie.color, "stroke-width": 2, "stroke-linejoin": "round" }),
    );
    rows.forEach((row, i) => {
      svg.append(
        svgEl("circle", {
          cx: xAt(i),
          cy: yAt(serie.get(row)),
          r: 4,
          fill: serie.color,
          stroke: "var(--surface)",
          "stroke-width": 2,
        }),
      );
    });
  });

  // crosshair: uma faixa por semana cobre as duas séries de uma vez
  rows.forEach((row, i) => {
    const hit = svgEl("rect", {
      class: "chart__hit",
      x: xAt(i) - stepX / 2,
      y: 12,
      width: stepX,
      height: plotHeight,
    });
    const rule = svgEl("line", {
      x1: xAt(i),
      y1: 12,
      x2: xAt(i),
      y2: 12 + plotHeight,
      stroke: "var(--axis)",
      "stroke-width": 1,
      opacity: 0,
    });
    svg.append(rule, hit);

    hit.addEventListener("mouseenter", (event) => {
      rule.setAttribute("opacity", "1");
      showTooltip(
        event,
        weekLabel(row.week),
        series.map((s) => ({ label: s.name, value: formatInteger(s.get(row)), color: s.color })),
      );
    });
    hit.addEventListener("mousemove", moveTooltip);
    hit.addEventListener("mouseleave", () => {
      rule.setAttribute("opacity", "0");
      hideTooltip();
    });

    if (i === 0 || i === rows.length - 1 || rows.length <= 4) {
      svg.append(
        Object.assign(
          svgEl("text", {
            x: xAt(i),
            y: height - 12,
            "text-anchor": i === 0 ? "start" : i === rows.length - 1 ? "end" : "middle",
          }),
          { textContent: shortDate(row.week) },
        ),
      );
    }
  });

  svg.append(
    svgEl("line", { class: "chart__axis", x1: padLeft, y1: 12 + plotHeight, x2: width - 12, y2: 12 + plotHeight }),
  );

  host.replaceChildren(
    legendFor(series.map((s) => ({ label: s.name, color: s.color }))),
    svg,
  );

  q("#history-table").innerHTML = buildTable(
    ["Semana", "Convertidos", "Descartados"],
    rows.map((r) => [formatDate(r.week), r.convertido, r.descartado]),
  );
}

function legendFor(items) {
  const wrap = document.createElement("div");
  wrap.className = "legend";
  wrap.innerHTML = items
    .map(
      (item) =>
        `<span class="legend__item"><span class="legend__swatch" style="background:${item.color}"></span>${escapeHtml(item.label)}</span>`,
    )
    .join("");
  return wrap;
}

function buildTable(headers, rows) {
  return `<table class="data-table">
      <thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows
        .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
        .join("")}</tbody>
    </table>`;
}

function redrawCharts() {
  if (!state.leads.length && !state.prospects.length) return;
  renderStageChart();
  renderWeekChart();
  renderHistoryChart();
}

/* =========================================================
   KPI
   ========================================================= */

function renderKpis() {
  const interactions = state.leads.reduce((acc, lead) => acc + lead.interaction_count, 0);
  const converted = state.prospects.filter((p) => p.status === "convertido").length;
  const urgent = getUrgentLeads().length;
  const overdue = getOverdueLeads().length;
  const totalProspects = state.prospects.length;
  const rate = totalProspects ? (converted / totalProspects) * 100 : 0;

  setKpi("stat-leads", formatInteger(state.leads.length), `${formatInteger(state.summary.cliente ?? 0)} já clientes`);
  setKpi(
    "stat-followups",
    formatInteger(urgent),
    overdue ? `${formatInteger(overdue)} atrasados` : "nenhum atrasado",
    overdue ? "down" : "up",
  );
  setKpi(
    "stat-interactions",
    formatInteger(interactions),
    `${(interactions / Math.max(1, state.leads.length)).toFixed(1)} por lead`,
  );
  setKpi("stat-converted", formatInteger(converted), `de ${formatInteger(totalProspects)} prospects`);
  setKpi("stat-rate", `${rate.toFixed(1)}%`, "prospect → lead");
}

function setKpi(id, value, deltaText, tone) {
  q(`#${id}`).textContent = value;
  const delta = q(`#${id}-delta`);
  delta.className = "kpi__delta" + (tone ? ` kpi__delta--${tone}` : "");
  // a seta acompanha a cor: quem não distingue verde de vermelho lê o glifo
  const arrow = tone === "up" ? "▲ " : tone === "down" ? "▼ " : "";
  delta.textContent = `${arrow}${deltaText}`;
}

function renderKpiSelection() {
  el.kpis.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.focus === state.focusFilter));
  });
}

/* =========================================================
   PIPELINE
   ========================================================= */

function renderPipeline() {
  const leads = getFilteredLeads();
  const grouped = groupBy(leads, "stage");

  el.pipelineTotal.textContent = `${formatInteger(leads.length)} de ${formatInteger(state.leads.length)} leads visíveis`;

  el.board.replaceChildren();

  STAGES.forEach(([key, label]) => {
    const column = document.createElement("div");
    const items = (grouped[key] ?? []).slice().sort(sortLeadsByUrgency);

    const head = document.createElement("div");
    head.className = "column__head";
    head.innerHTML = `<span class="column__name">${escapeHtml(label)}</span><span class="column__count">${items.length}</span>`;
    column.append(head);

    const cards = document.createElement("div");
    cards.className = "column__cards";

    if (!items.length) {
      cards.innerHTML = `<p class="column__empty">Sem leads.</p>`;
    } else {
      items.forEach((lead) => cards.append(createLeadCard(lead)));
    }

    column.append(cards);
    el.board.append(column);
  });
}

function createLeadCard(lead) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "lead-card";
  card.setAttribute("aria-pressed", String(lead.id === state.selectedLeadId));
  card.innerHTML = `
    <span class="lead-card__company">${escapeHtml(lead.company_name)}</span>
    <p class="lead-card__contact">${escapeHtml(lead.contact_name)}</p>
    <p class="lead-card__action">${escapeHtml(lead.next_action || "Sem próxima ação")}</p>
    <div class="lead-card__footer">
      <span>${escapeHtml(SOURCE_LABELS[lead.source] ?? lead.source)}</span>
      <span>${escapeHtml(describeUrgency(lead.next_action_date))}</span>
    </div>`;
  card.addEventListener("click", () => selectLead(lead.id));
  return card;
}

async function selectLead(leadId) {
  state.selectedLeadId = leadId;
  renderPipeline();

  if (!state.leadDetails.has(leadId)) {
    try {
      state.leadDetails.set(leadId, await api(`/leads/${leadId}`));
    } catch (error) {
      el.leadDetail.innerHTML = `<p class="empty">${escapeHtml(extractErrorMessage(error))}</p>`;
      return;
    }
  }

  renderLeadDetail(state.leadDetails.get(leadId));
}

function renderLeadDetail(lead) {
  const interactions = lead.interactions.slice().sort((a, b) => b.date.localeCompare(a.date));
  const urgency = urgencyBadge(lead.next_action_date, lead.stage);

  el.leadDetail.innerHTML = `
    <p class="detail__title">${escapeHtml(lead.company_name)}</p>
    <p class="detail__sub">${escapeHtml(lead.contact_name)} · ${escapeHtml(stageLabel(lead.stage))}</p>
    <dl class="detail__grid">
      <div class="detail__cell"><dt>Origem</dt><dd>${escapeHtml(SOURCE_LABELS[lead.source] ?? lead.source)}</dd></div>
      <div class="detail__cell"><dt>Interações</dt><dd>${interactions.length}</dd></div>
      <div class="detail__cell"><dt>Próxima ação</dt><dd>${escapeHtml(lead.next_action || "Não definida")}</dd></div>
      <div class="detail__cell"><dt>Quando</dt><dd>${urgency}</dd></div>
    </dl>
    <div class="timeline">
      ${
        interactions.length
          ? interactions
              .map(
                (item) => `<article class="timeline__item">
                    <div class="timeline__meta"><span>${escapeHtml(INTERACTION_LABELS[item.type] ?? item.type)}</span><span>${formatDate(item.date)}</span></div>
                    <p class="timeline__text">${escapeHtml(item.description)}</p>
                  </article>`,
              )
              .join("")
          : `<p class="empty">Nenhuma interação registrada.</p>`
      }
    </div>`;
}

/** Status sempre com ícone + rótulo: a cor nunca carrega o sentido sozinha. */
function urgencyBadge(dateValue, stage) {
  if (!dateValue) {
    return `<span class="badge">Sem data</span>`;
  }
  if (["cliente", "sem_momento"].includes(stage)) {
    return `<span class="badge">${escapeHtml(formatDate(dateValue))}</span>`;
  }
  const diff = dateDiffInDays(dateValue);
  if (diff < 0) {
    return `<span class="badge badge--critical"><span class="badge__icon" aria-hidden="true">!</span>${Math.abs(diff)}d atrasado</span>`;
  }
  if (diff <= 1) {
    return `<span class="badge badge--warning"><span class="badge__icon" aria-hidden="true">•</span>${diff === 0 ? "Hoje" : "Amanhã"}</span>`;
  }
  return `<span class="badge badge--good"><span class="badge__icon" aria-hidden="true">✓</span>em ${diff}d</span>`;
}

/* =========================================================
   PROSPECTS E CONVERSÃO
   ========================================================= */

function renderProspects() {
  const prospects = eligibleProspects();
  el.conversionCount.textContent = `${formatInteger(prospects.length)} prospects elegíveis nesta semana`;
  el.prospectList.replaceChildren();

  if (!prospects.length) {
    el.prospectList.innerHTML = `<p class="empty">Nenhum prospect elegível na semana.</p>`;
    return;
  }

  prospects.forEach((prospect) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "prospect";
    button.setAttribute("aria-pressed", String(prospect.id === state.selectedProspectId));
    button.innerHTML = `
      <span class="prospect__name">${escapeHtml(prospect.company_name)}</span>
      <span class="prospect__meta">${escapeHtml(SEGMENT_LABELS[prospect.segment] ?? prospect.segment ?? "—")} · ${escapeHtml(STATUS_LABELS[prospect.status] ?? prospect.status)}</span>`;
    button.addEventListener("click", () => selectProspect(prospect.id));
    el.prospectList.append(button);
  });
}

function selectProspect(prospectId) {
  const prospect = state.prospects.find((item) => item.id === prospectId);
  if (!prospect) return;

  state.selectedProspectId = prospectId;
  el.convertCompany.value = prospect.company_name;
  el.convertContactName.value = prospect.contact_name || "";
  el.convertPhone.value = prospect.phone || "";
  el.convertEmail.value = prospect.email || "";
  el.convertNotes.value = prospect.signals || prospect.notes || "";
  el.convertSubmit.disabled = false;
  setFeedback(`${prospect.company_name} pronto para conversão.`);
  renderProspects();
}

async function handleConversionSubmit(event) {
  event.preventDefault();
  if (!state.selectedProspectId) return;

  const payload = {
    contact_name: el.convertContactName.value.trim(),
    phone: optionalField(el.convertPhone.value),
    email: optionalField(el.convertEmail.value),
    notes: optionalField(el.convertNotes.value),
  };

  if (!payload.contact_name) {
    setFeedback("Informe o nome do contato para converter.", "error");
    return;
  }

  el.convertSubmit.disabled = true;
  setFeedback("Convertendo prospect...");

  try {
    const converted = await api(`/prospects/${state.selectedProspectId}/convert`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    setFeedback(`Convertido. Lead #${converted.lead_id} entrou em Qualificando.`, "ok");
    state.leadDetails.clear();
    state.selectedLeadId = null;
    state.selectedProspectId = null;
    resetConversionFields();
    await loadAllData({ keepLead: false, keepWeek: true });
    if (converted.lead_id) await selectLead(converted.lead_id);
  } catch (error) {
    el.convertSubmit.disabled = false;
    setFeedback(extractErrorMessage(error), "error");
  }
}

function clearConversionSelection() {
  state.selectedProspectId = null;
  resetConversionFields();
  setFeedback("");
  renderProspects();
}

function resetConversionFields() {
  el.convertCompany.value = "";
  el.convertContactName.value = "";
  el.convertPhone.value = "";
  el.convertEmail.value = "";
  el.convertNotes.value = "";
  el.convertSubmit.disabled = true;
}

/* =========================================================
   ATIVIDADE
   ========================================================= */

function renderActivityFeed() {
  const items = [];

  getOverdueLeads().forEach((lead) => {
    items.push({
      title: lead.company_name,
      text: `Ação atrasada: ${lead.next_action || "sem descrição"} (${describeUrgency(lead.next_action_date)})`,
      order: 0,
    });
  });

  getUrgentLeads()
    .filter((lead) => dateDiffInDays(lead.next_action_date) >= 0)
    .forEach((lead) => {
      items.push({
        title: lead.company_name,
        text: `${lead.next_action || "Próxima ação"} — ${describeUrgency(lead.next_action_date)}`,
        order: 1,
      });
    });

  getNoDateLeads().forEach((lead) => {
    items.push({ title: lead.company_name, text: "Sem próxima ação definida.", order: 2 });
  });

  el.activityFeed.replaceChildren();

  if (!items.length) {
    el.activityFeed.innerHTML = `<p class="empty">Nada exigindo atenção agora.</p>`;
    return;
  }

  items
    .sort((a, b) => a.order - b.order)
    .slice(0, 14)
    .forEach((item) => {
      const node = document.createElement("div");
      node.className = "feed__item";
      node.innerHTML = `<span class="feed__dot" aria-hidden="true"></span>
        <div class="feed__body"><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.text)}</p></div>`;
      el.activityFeed.append(node);
    });
}

/* =========================================================
   SELECT DE SEMANA / STATUS
   ========================================================= */

function renderWeekSelect() {
  el.weekSelect.replaceChildren();
  state.weeks.forEach((week) => {
    const option = document.createElement("option");
    option.value = week;
    option.textContent = formatDate(week);
    option.selected = week === state.selectedWeek;
    el.weekSelect.append(option);
  });
}

function updateStatus() {
  const visible = getFilteredLeads().length;
  const urgent = getUrgentLeads().length;
  setStatus(`${visible} leads visíveis, ${urgent} em janela crítica.`);
}

function renderGlobalError(error) {
  const message = extractErrorMessage(error);
  el.board.innerHTML = `<p class="empty">${escapeHtml(message)}</p>`;
  el.prospectList.innerHTML = "";
  el.leadDetail.innerHTML = `<p class="empty">${escapeHtml(message)}</p>`;
  setStatus(message);
}

/* =========================================================
   SELETORES DE DADOS
   ========================================================= */

function getFilteredLeads() {
  return state.leads.filter((lead) => {
    const matchesSearch =
      !state.search || `${lead.company_name} ${lead.contact_name}`.toLowerCase().includes(state.search);
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

function eligibleProspects() {
  return state.prospects.filter(
    (prospect) =>
      prospect.week === state.selectedWeek &&
      ["pesquisando", "qualificado", "contactado"].includes(prospect.status),
  );
}

function sortLeadsByUrgency(a, b) {
  const diff = urgencyScore(a.next_action_date) - urgencyScore(b.next_action_date);
  return diff || a.company_name.localeCompare(b.company_name);
}

function urgencyScore(dateValue) {
  return dateValue ? dateDiffInDays(dateValue) : Number.MAX_SAFE_INTEGER;
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

/* =========================================================
   UTILITÁRIOS
   ========================================================= */

function q(selector) {
  return document.querySelector(selector);
}

function groupBy(items, key) {
  return items.reduce((groups, item) => {
    (groups[item[key]] = groups[item[key]] || []).push(item);
    return groups;
  }, {});
}

function deriveWeeks(prospects) {
  return Array.from(new Set(prospects.map((p) => p.week).filter(Boolean))).sort();
}

function stageLabel(stage) {
  return STAGES.find(([key]) => key === stage)?.[1] ?? stage;
}

function formatDate(value) {
  if (!value) return "Sem data";
  return new Date(`${value}T12:00:00`).toLocaleDateString("pt-BR");
}

function shortDate(value) {
  return new Date(`${value}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

function weekLabel(week) {
  return `Semana de ${formatDate(week)}`;
}

function formatInteger(value) {
  return new Intl.NumberFormat("pt-BR").format(value);
}

function optionalField(value) {
  return value.trim() || null;
}

function setFeedback(message, tone) {
  el.conversionFeedback.textContent = message;
  if (tone) {
    el.conversionFeedback.dataset.tone = tone;
  } else {
    delete el.conversionFeedback.dataset.tone;
  }
}

function setStatus(message) {
  el.dashboardStatus.textContent = message;
}

function extractErrorMessage(error) {
  return error instanceof Error ? error.message : "Erro inesperado.";
}

function debounce(fn, wait) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

/**
 * Escapa texto que vai para `innerHTML`.
 *
 * Nome de empresa, contato, notas e sinais são campos livres da API: sem isto,
 * uma empresa chamada "Auto Peças <Vinhedo>" quebra a renderização, e um campo
 * com `<img src=x onerror=...>` executa script na página.
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
