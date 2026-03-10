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
  const fallbackHotspots = riskCells.value.slice(0, 6).map((cell) => ({
    grid_key: `${cell.grid_lat}-${cell.grid_lon}`,
    grid_lat: cell.grid_lat,
    grid_lon: cell.grid_lon,
    vessel_count: cell.vessel_count,
    anomaly_score_mean: cell.rri_score,
    rri_score: cell.rri_score,
    risk_level: cell.risk_level,
  }));
  return {
    window_label: summary.value?.window_label || "",
    vessel_count: vessels.value.length,
    anomaly_level_counts: {
      highly_abnormal: Math.min(6, ranked.length),
      suspicious: Math.min(12, Math.max(ranked.length - 6, 0)),
      normal: Math.max(vessels.value.length - 18, 0),
      observation_insufficient: 0,
    },
    anomaly_type_counts: {
      long_dwell_low_speed: Math.min(6, ranked.length),
      warm_productive_water: Math.min(4, Math.max(ranked.length - 6, 0)),
      mixed_anomaly: Math.max(Math.min(8, Math.max(ranked.length - 10, 0)), 0),
      sparse_observation: 0,
    },
    anomaly_type_profiles: [
      {
        anomaly_type: "long_dwell_low_speed",
        anomaly_type_label: "长时低速型",
        vessel_count: Math.min(6, ranked.length),
        summary: "当前回退样本显示出较长时间低速停留的共同特征。",
        key_metrics: [
          { metric_key: "low_speed_ratio", metric_label: "低速暴露比例", type_mean: 0.92, normal_mean: 0.41, delta: 0.51, direction: "higher" },
          { metric_key: "track_duration_hours", metric_label: "轨迹时长", type_mean: 300, normal_mean: 120, delta: 180, direction: "higher" },
        ],
      },
      {
        anomaly_type: "warm_productive_water",
        anomaly_type_label: "高温高叶绿素型",
        vessel_count: Math.min(4, Math.max(ranked.length - 6, 0)),
        summary: "当前回退样本显示出更高的海温与叶绿素暴露。",
        key_metrics: [
          { metric_key: "mean_sst", metric_label: "平均海温暴露", type_mean: 28.3, normal_mean: 27.4, delta: 0.9, direction: "higher" },
          { metric_key: "mean_chlorophyll_a", metric_label: "平均叶绿素暴露", type_mean: 0.42, normal_mean: 0.23, delta: 0.19, direction: "higher" },
        ],
      },
    ],
    anomaly_type_spatial_slices: [
      {
        anomaly_type: "long_dwell_low_speed",
        anomaly_type_label: "闀挎椂浣庨€熷瀷",
        vessel_count: Math.min(6, ranked.length),
        highlighted_cells: fallbackHotspots.length,
        summary: "鍥為€€鏍锋湰涓紝璇ョ被鍨嬩富瑕佸湪褰撳墠楂橀闄╂牸缃戝懆杈瑰嚭鐜帮紝鐢ㄤ簬淇濇寔鍦板浘浜や簰涓嶄腑鏂€?",
        top_hotspots: fallbackHotspots,
      },
      {
        anomaly_type: "warm_productive_water",
        anomaly_type_label: "楂樻俯楂樺彾缁跨礌鍨?",
        vessel_count: Math.min(4, Math.max(ranked.length - 6, 0)),
        highlighted_cells: Math.max(fallbackHotspots.length - 2, 1),
        summary: "鍥為€€鏍锋湰涓紝璇ョ被鍨嬩富瑕佽仛闆嗗湪姘村煙鏉′欢杈冧负绐佸嚭鐨勫尯鍩熴€?",
        top_hotspots: fallbackHotspots.slice(0, 4),
      },
      {
        anomaly_type: "mixed_anomaly",
        anomaly_type_label: "娣峰悎寮傚父鍨?",
        vessel_count: Math.max(Math.min(8, Math.max(ranked.length - 10, 0)), 0),
        highlighted_cells: Math.max(fallbackHotspots.length - 1, 1),
        summary: "鍥為€€鏍锋湰涓紝璇ョ被鍨嬪湪澶氱被椹卞姩鍥犵礌鍚屾椂鍋忕鐨勭儹鐐瑰尯鍩熸洿涓洪泦涓€?",
        top_hotspots: fallbackHotspots.slice(0, 5),
      },
      {
        anomaly_type: "sparse_observation",
        anomaly_type_label: "瑙傛祴绋€鐤忓瀷",
        vessel_count: 0,
        highlighted_cells: Math.max(fallbackHotspots.length - 3, 1),
        summary: "鍥為€€鏍锋湰涓紝璇ョ被鍨嬩富瑕佺敤浜庢彁绀鸿娴嬩笉瓒崇殑绌洪棿鍒嗗竷銆?",
        top_hotspots: fallbackHotspots.slice(0, 3),
      },
    ],
    top_anomalies: ranked.slice(0, 12).map((item, index) => ({
      rank: index + 1,
      mmsi: item.mmsi,
      anomaly_score: item.fpi_proxy,
      anomaly_level: index < 6 ? "highly_abnormal" : "suspicious",
      anomaly_severity: index < 6 ? "高" : "中",
      anomaly_type: index < 6 ? "long_dwell_low_speed" : "mixed_anomaly",
      anomaly_type_label: index < 6 ? "长时低速型" : "混合异常型",
      anomaly_type_summary:
        index < 6 ? "当前回退样本显示出较长时间的低速停留特征。" : "当前回退样本存在多项偏离信号。",
      dominant_evidence: index < 6 ? "低速暴露比例偏高" : "多项信号共同偏离",
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
        anomaly_severity: match.anomaly_severity || "中",
        percentile_rank: Number((1 - (match.rank - 1) / Math.max(fallbackSummary.vessel_count - 1, 1)).toFixed(4)),
        anomaly_type: match.anomaly_type || "mixed_anomaly",
        anomaly_type_label: match.anomaly_type_label || "混合异常型",
        anomaly_type_summary: match.anomaly_type_summary || "当前回退结果未提供更细的异常类型解释。",
        dominant_evidence_title: match.dominant_evidence || "主导证据待补充",
        dominant_evidence_summary: "当前回退结果未提供结构化主导证据。",
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
      anomaly_severity: "低",
      anomaly_type: "mixed_anomaly",
      anomaly_type_label: "混合异常型",
      anomaly_type_summary: "当前没有可用的异常类型结果。",
      dominant_evidence_title: null,
      dominant_evidence_summary: null,
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
