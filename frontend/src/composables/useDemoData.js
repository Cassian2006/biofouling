import { computed, ref } from "vue";

const summary = ref(null);
const vessels = ref([]);
const riskCells = ref([]);
const loading = ref(false);
const error = ref("");
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
let loadPromise = null;

function buildApiUrl(path) {
  return apiBaseUrl ? `${apiBaseUrl}${path}` : path;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`加载演示数据失败: ${response.status}`);
  }
  return response.json();
}

async function fetchJsonWithFallback(primaryUrl, fallbackUrl) {
  try {
    return await fetchJson(primaryUrl);
  } catch (primaryError) {
    if (!fallbackUrl) {
      throw primaryError;
    }
    return fetchJson(fallbackUrl);
  }
}

function buildRegionalStatsFallback() {
  const counts = { high: 0, medium: 0, low: 0 };
  for (const cell of riskCells.value) {
    counts[cell.risk_level] = (counts[cell.risk_level] || 0) + 1;
  }

  const average = (key) => {
    const values = riskCells.value
      .map((item) => item[key])
      .filter((value) => value !== null && value !== undefined);
    if (!values.length) return null;
    return Number((values.reduce((total, value) => total + value, 0) / values.length).toFixed(3));
  };

  return {
    window_label: summary.value?.window_label || "",
    total_cells: riskCells.value.length,
    risk_level_counts: counts,
    average_rri: average("rri_score"),
    average_traffic_score: average("traffic_score"),
    average_low_speed_score: average("low_speed_score"),
    average_environment_score: average("environment_score"),
    top_cell: riskCells.value[0] || null,
    top_cells: riskCells.value.slice(0, 10),
  };
}

function buildVesselDetailFallback(mmsi) {
  const vessel = vessels.value.find((item) => item.mmsi === String(mmsi));
  if (!vessel) {
    throw new Error(`未找到船舶 ${mmsi}`);
  }
  return {
    window_label: summary.value?.window_label || "",
    vessel,
    cohort_size: vessels.value.length,
    rank_fraction: `${vessel.rank} / ${vessels.value.length}`,
    peer_vessels: vessels.value.filter((item) => item.mmsi !== vessel.mmsi).slice(0, 8),
  };
}

function buildVesselReportFallback(mmsi) {
  const vessel = vessels.value.find((item) => item.mmsi === String(mmsi));
  if (!vessel) {
    throw new Error(`未找到船舶 ${mmsi}`);
  }
  const lines = [
    `Track window: ${vessel.track_start} -> ${vessel.track_end}`,
    `Ping count: ${vessel.ping_count}`,
    `Low-speed ratio: ${vessel.low_speed_ratio}`,
    `FPI proxy: ${vessel.fpi_proxy}`,
    `ECP proxy: ${vessel.ecp_proxy}`,
    `Recommendation: ${vessel.recommendation}`,
  ];
  return {
    window_label: summary.value?.window_label || "",
    scope: "vessel",
    title: `MMSI ${vessel.mmsi} report preview`,
    markdown: lines.join("\n"),
    lines,
  };
}

async function fetchDemoData() {
  if ((summary.value && vessels.value.length && riskCells.value.length) || loadPromise) {
    return loadPromise;
  }

  loading.value = true;
  loadPromise = Promise.all([
    fetchJsonWithFallback(buildApiUrl("/api/demo/summary"), "/demo/summary.json"),
    fetchJsonWithFallback(buildApiUrl("/api/demo/vessels"), "/demo/vessels.json"),
    fetchJsonWithFallback(buildApiUrl("/api/demo/risk-cells"), "/demo/risk_cells.json"),
  ])
    .then(([summaryData, vesselData, riskCellData]) => {
      summary.value = summaryData;
      vessels.value = vesselData;
      riskCells.value = riskCellData;
      error.value = "";
      return { summary: summaryData, vessels: vesselData, riskCells: riskCellData };
    })
    .catch((err) => {
      error.value = err instanceof Error ? err.message : "未知错误";
      throw err;
    })
    .finally(() => {
      loading.value = false;
      loadPromise = null;
    });

  return loadPromise;
}

async function fetchVesselDetail(mmsi) {
  await fetchDemoData();
  try {
    return await fetchJson(buildApiUrl(`/api/demo/vessels/${mmsi}`));
  } catch (errorObject) {
    return buildVesselDetailFallback(mmsi);
  }
}

async function fetchVesselTrack(mmsi) {
  await fetchDemoData();
  return fetchJson(buildApiUrl(`/api/demo/vessels/${mmsi}/track`));
}

async function fetchVesselTrend(mmsi) {
  await fetchDemoData();
  return fetchJson(buildApiUrl(`/api/demo/vessels/${mmsi}/trend`));
}

async function fetchRegionalStats() {
  await fetchDemoData();
  try {
    return await fetchJson(buildApiUrl("/api/demo/regional-stats"));
  } catch (errorObject) {
    return buildRegionalStatsFallback();
  }
}

async function fetchVesselReportPreview(mmsi) {
  await fetchDemoData();
  try {
    return await fetchJson(buildApiUrl(`/api/demo/reports/vessels/${mmsi}`));
  } catch (errorObject) {
    return buildVesselReportFallback(mmsi);
  }
}

async function fetchOverviewReportPreview() {
  await fetchDemoData();
  try {
    return await fetchJson(buildApiUrl("/api/demo/reports/overview"));
  } catch (errorObject) {
    return {
      window_label: summary.value?.window_label || "",
      scope: "overview",
      title: "Voyage report overview",
      markdown: `Window: ${summary.value?.window_label || ""}\nVessels: ${summary.value?.vessels_summarized || 0}\nGrid cells: ${summary.value?.grid_cells || 0}`,
      lines: [
        `Window: ${summary.value?.window_label || ""}`,
        `Vessels: ${summary.value?.vessels_summarized || 0}`,
        `Grid cells: ${summary.value?.grid_cells || 0}`,
      ],
    };
  }
}

export function useDemoData() {
  const hasData = computed(() => Boolean(summary.value));

  return {
    summary,
    vessels,
    riskCells,
    loading,
    error,
    hasData,
    fetchDemoData,
    fetchVesselDetail,
    fetchVesselTrack,
    fetchVesselTrend,
    fetchRegionalStats,
    fetchVesselReportPreview,
    fetchOverviewReportPreview,
  };
}
