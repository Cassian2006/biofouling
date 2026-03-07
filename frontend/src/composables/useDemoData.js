import { computed, ref } from "vue";

const summary = ref(null);
const vessels = ref([]);
const riskCells = ref([]);
const anomalySummary = ref(null);
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
    reference_sites: [],
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
    static_profile: null,
    validation_summary: {
      mmsi: vessel.mmsi,
      event_count: 0,
      source_count: 0,
      sources: [],
      latest_event_type: null,
      latest_event_start: null,
      latest_port_name: null,
      notes_count: 0,
    },
    nearest_reference: null,
    nearest_reference_distance_km: null,
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

async function fetchVesselForecast(mmsi) {
  await fetchDemoData();
  return fetchJson(buildApiUrl(`/api/demo/vessels/${mmsi}/forecast`));
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

function buildAnomalySummaryFallback() {
  const ranked = [...vessels.value]
    .filter((item) => item.fpi_proxy !== null && item.fpi_proxy !== undefined)
    .sort((left, right) => (right.fpi_proxy || 0) - (left.fpi_proxy || 0));
  return {
    window_label: summary.value?.window_label || "",
    vessel_count: vessels.value.length,
    anomaly_level_counts: {
      highly_abnormal: Math.min(6, ranked.length),
      suspicious: Math.min(12, Math.max(ranked.length - 6, 0)),
      normal: Math.max(vessels.value.length - 18, 0),
      observation_insufficient: 0,
    },
    top_anomalies: ranked.slice(0, 12).map((item, index) => ({
      rank: index + 1,
      mmsi: item.mmsi,
      anomaly_score: item.fpi_proxy,
      anomaly_level: index < 6 ? "highly_abnormal" : "suspicious",
      explanations: ["当前回退为静态演示数据，异常解释未接入。"],
      summary_sentence: "当前为静态回退结果，暂未生成正式异常结论。",
    })),
  };
}

async function fetchAnomalySummary() {
  await fetchDemoData();
  try {
    const payload = await fetchJson(buildApiUrl("/api/demo/anomalies"));
    anomalySummary.value = payload;
    return payload;
  } catch (errorObject) {
    const fallback = buildAnomalySummaryFallback();
    anomalySummary.value = fallback;
    return fallback;
  }
}

async function fetchVesselAnomaly(mmsi) {
  await fetchDemoData();
  try {
    return await fetchJson(buildApiUrl(`/api/demo/vessels/${mmsi}/anomaly`));
  } catch (errorObject) {
    const fallbackSummary = anomalySummary.value || buildAnomalySummaryFallback();
    const match = fallbackSummary.top_anomalies.find((item) => item.mmsi === String(mmsi));
    if (match) {
      return {
        window_label: fallbackSummary.window_label,
        mmsi: String(mmsi),
        anomaly_score: match.anomaly_score,
        anomaly_level: match.anomaly_level,
        percentile_rank: Number((1 - (match.rank - 1) / Math.max(fallbackSummary.vessel_count - 1, 1)).toFixed(4)),
        summary_sentence: match.summary_sentence,
        explanations: match.explanations,
        driver_details: [],
        peer_anomalies: fallbackSummary.top_anomalies.filter((item) => item.mmsi !== String(mmsi)).slice(0, 6),
      };
    }
    return {
      window_label: fallbackSummary.window_label,
      mmsi: String(mmsi),
      anomaly_score: 0,
      anomaly_level: "normal",
      percentile_rank: 0.5,
      summary_sentence: "当前没有可用的异常检测结果。",
      explanations: ["当前没有可用的异常检测结果。"],
      driver_details: [],
      peer_anomalies: fallbackSummary.top_anomalies.slice(0, 6),
    };
  }
}

export function useDemoData() {
  const hasData = computed(() => Boolean(summary.value));

  return {
    summary,
    vessels,
    riskCells,
    anomalySummary,
    loading,
    error,
    hasData,
    fetchDemoData,
    fetchVesselDetail,
    fetchVesselTrack,
    fetchVesselTrend,
    fetchVesselForecast,
    fetchRegionalStats,
    fetchVesselReportPreview,
    fetchOverviewReportPreview,
    fetchAnomalySummary,
    fetchVesselAnomaly,
  };
}
