<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import HintTooltip from "../components/HintTooltip.vue";
import VesselTrackMap from "../components/VesselTrackMap.vue";
import { useDemoData } from "../composables/useDemoData";

const route = useRoute();
const router = useRouter();
const {
  summary,
  vessels,
  loading,
  error,
  fetchDemoData,
  fetchVesselAnomaly,
  fetchVesselDetail,
  fetchVesselForecast,
  fetchVesselReportPreview,
  fetchVesselTrack,
  fetchVesselTrend,
} = useDemoData();

const vesselDetail = ref(null);
const vesselTrack = ref(null);
const vesselTrend = ref(null);
const vesselForecast = ref(null);
const vesselAnomaly = ref(null);
const reportPreview = ref(null);
const pageError = ref("");
const trackError = ref("");
const trendError = ref("");
const forecastError = ref("");
const anomalyError = ref("");
const selectedMmsi = ref("");
const selectedTrendWindowIndex = ref(null);

const selectedVessel = computed(() => vesselDetail.value?.vessel || null);
const staticProfile = computed(() => vesselDetail.value?.static_profile || null);
const validationSummary = computed(() => vesselDetail.value?.validation_summary || null);
const nearestReference = computed(() => vesselDetail.value?.nearest_reference || null);
const forecastSignals = computed(() => vesselForecast.value?.signals || []);
const forecastHistoryPoints = computed(() => vesselForecast.value?.history_points || []);
const forecastAvailable = computed(() => Boolean(vesselForecast.value?.available));
const focusAnomalyType = computed(() => (route.query.anomalyType ? String(route.query.anomalyType) : ""));

const vesselOptions = computed(() =>
  vessels.value.map((item) => ({
    value: item.mmsi,
    label: `#${item.rank}  ${item.mmsi}  |  FPI ${item.fpi_proxy ?? "暂无"}  |  ${item.recommendation}`,
  })),
);

function buildAssessment(values, value) {
  const numericValues = values.filter((item) => Number.isFinite(item)).sort((left, right) => left - right);
  if (!Number.isFinite(value) || numericValues.length < 3) return null;
  const lower = numericValues[Math.floor((numericValues.length - 1) * 0.33)];
  const upper = numericValues[Math.floor((numericValues.length - 1) * 0.67)];
  if (value <= lower) return "相对较低";
  if (value >= upper) return "相对较高";
  return "中等";
}

function anomalyLevelLabel(level) {
  if (level === "highly_abnormal") return "高度异常";
  if (level === "suspicious") return "需复核";
  if (level === "observation_insufficient") return "观测不足";
  return "正常";
}

function anomalyTypeLabel(type) {
  if (type === "long_dwell_low_speed") return "长时低速型";
  if (type === "warm_productive_water") return "高温高叶绿素型";
  if (type === "mixed_anomaly") return "混合异常型";
  if (type === "sparse_observation") return "观测稀疏型";
  return type || "异常类型";
}

function riskLabelText(level) {
  if (level === "high") return "高风险";
  if (level === "medium") return "中风险";
  if (level === "low") return "低风险";
  return level || "风险待定";
}

const vesselFacts = computed(() => {
  if (!selectedVessel.value) return [];
  const sstValues = vessels.value.map((item) => item.mean_sst);
  const chlorophyllValues = vessels.value.map((item) => item.mean_chlorophyll_a);
  const salinityValues = vessels.value.map((item) => item.mean_salinity);
  const lowSpeedValues = vessels.value.map((item) => item.low_speed_ratio);
  const durationValues = vessels.value.map((item) => item.track_duration_hours);
  const currentIntensityValues = vessels.value.map((item) => {
    if (item.mean_current_u === null || item.mean_current_v === null) return null;
    return Math.hypot(item.mean_current_u, item.mean_current_v);
  });
  const currentIntensity =
    selectedVessel.value.mean_current_u !== null && selectedVessel.value.mean_current_v !== null
      ? Math.hypot(selectedVessel.value.mean_current_u, selectedVessel.value.mean_current_v)
      : null;

  return [
    {
      title: "轨迹时间窗",
      value: `${selectedVessel.value.track_start} -> ${selectedVessel.value.track_end}`,
      description: "对应本轮研究窗口内的实际 AIS 记录时间范围。",
      assessment: null,
    },
    {
      title: "轨迹点数与时长",
      value: `${selectedVessel.value.ping_count} 点 / ${selectedVessel.value.track_duration_hours} 小时`,
      description: "点数与时间跨度决定该对象的观测充分性。",
      assessment: buildAssessment(durationValues, selectedVessel.value.track_duration_hours),
    },
    {
      title: "低速暴露比例",
      value: selectedVessel.value.low_speed_ratio ?? "暂无",
      description: "用于衡量低速、停留或等待行为在整段轨迹中的占比。",
      assessment: buildAssessment(lowSpeedValues, selectedVessel.value.low_speed_ratio),
    },
    {
      title: "平均海温暴露",
      value: selectedVessel.value.mean_sst ?? "暂无",
      description: "基于真实环境匹配结果计算的平均海温暴露。",
      assessment: buildAssessment(sstValues, selectedVessel.value.mean_sst),
    },
    {
      title: "平均叶绿素暴露",
      value: selectedVessel.value.mean_chlorophyll_a ?? "暂无",
      description: "用于表示生物活跃环境的相对水平。",
      assessment: buildAssessment(chlorophyllValues, selectedVessel.value.mean_chlorophyll_a),
    },
    {
      title: "平均盐度暴露",
      value: selectedVessel.value.mean_salinity ?? "暂无",
      description: "用于区分不同水体环境下的暴露差异。",
      assessment: buildAssessment(salinityValues, selectedVessel.value.mean_salinity),
    },
    {
      title: "海流强度",
      value:
        selectedVessel.value.mean_current_u !== null && selectedVessel.value.mean_current_v !== null
          ? `${selectedVessel.value.mean_current_u} / ${selectedVessel.value.mean_current_v}`
          : "暂无",
      description: "以 U/V 分量表示的平均海流方向与强度。",
      assessment: buildAssessment(currentIntensityValues, currentIntensity),
    },
  ];
});

const staticFacts = computed(() => {
  if (!staticProfile.value) return [];
  return [
    {
      title: "画像来源",
      value: staticProfile.value.profile_source,
      description: "说明当前画像来自 AIS 派生结果，或已融合外部静态资料。",
    },
    {
      title: "船名 / IMO",
      value: `${staticProfile.value.vessel_name || "暂无"} / ${staticProfile.value.imo || "暂无"}`,
      description: "接入完整外部静态资料后，此处会显示更完整的识别信息。",
    },
    {
      title: "船型 / 船旗",
      value: `${staticProfile.value.ship_type || "暂无"} / ${staticProfile.value.flag || "暂无"}`,
      description: "用于支持船型分层和辅助解释。",
    },
    {
      title: "长度 / 型宽",
      value:
        staticProfile.value.length_m !== null && staticProfile.value.beam_m !== null
          ? `${staticProfile.value.length_m} m / ${staticProfile.value.beam_m} m`
          : "暂无",
      description: "在有外部资料时，会优先显示更准确的尺度信息。",
    },
    {
      title: "最近港口 / 锚地",
      value: nearestReference.value ? `${nearestReference.value.name}（${nearestReference.value.site_type}）` : "暂无",
      description: nearestReference.value
        ? `按船舶平均位置匹配，距离约 ${vesselDetail.value?.nearest_reference_distance_km ?? "暂无"} km。`
        : "当前没有可用的港口或锚地参考点匹配。",
    },
  ];
});

const validationFacts = computed(() => {
  if (!validationSummary.value) return [];
  return [
    {
      title: "外部校验事件数",
      value: validationSummary.value.event_count,
      description: "用于判断当前是否已有外部事件可与模型结果相互印证。",
    },
    {
      title: "最近校验事件",
      value: validationSummary.value.latest_event_type || "暂无",
      description: "后续接入离港、进港或维护事件后，可在此查看最近记录。",
    },
    {
      title: "最近事件位置",
      value: validationSummary.value.latest_port_name || "暂无",
      description: "用于将分析判断与真实港口或案例位置对齐。",
    },
  ];
});

const vesselHeroHighlights = computed(() => {
  if (!selectedVessel.value) return [];
  return [
    {
      title: "当前建议",
      description: selectedVessel.value.recommendation,
    },
    {
      title: "异常类型",
      description: vesselAnomaly.value?.anomaly_type_label || "待识别",
    },
    {
      title: "轨迹跨度",
      description: `${selectedVessel.value.track_duration_hours ?? "暂无"} 小时`,
    },
    {
      title: "最近参考点",
      description: nearestReference.value?.name || "暂无匹配",
    },
  ];
});

const compactSummary = computed(() => {
  if (!selectedVessel.value || !vesselTrack.value) return "";
  const forecastSummary = vesselForecast.value
    ? forecastAvailable.value
      ? `下一时间窗预测 FPI ${vesselForecast.value.predicted_fpi}，预测等级 ${riskLabelText(vesselForecast.value.predicted_risk_label)}。`
      : "当前对象暂未生成 LSTM 预测。"
    : "";
  const anomalySummary = vesselAnomaly.value
    ? `异常等级 ${anomalyLevelLabel(vesselAnomaly.value.anomaly_level)}，异常分数 ${vesselAnomaly.value.anomaly_score}。`
    : "";
  return `轨迹记录 ${vesselTrack.value.point_count} 点，时间跨度 ${selectedVessel.value.track_duration_hours} 小时，低速暴露比例 ${selectedVessel.value.low_speed_ratio ?? "暂无"}，建议为“${selectedVessel.value.recommendation}”。${forecastSummary}${anomalySummary}`;
});

const anomalyHeadline = computed(() => {
  if (!vesselAnomaly.value) return null;
  return {
    label: anomalyLevelLabel(vesselAnomaly.value.anomaly_level),
    percentile: `${Math.round((vesselAnomaly.value.percentile_rank || 0) * 100)}%`,
  };
});

const anomalyPeers = computed(() => vesselAnomaly.value?.peer_anomalies || []);

const selectedTrendWindow = computed(() => {
  if (!vesselTrend.value?.windows?.length) return null;
  if (selectedTrendWindowIndex.value === null) return null;
  const point = vesselTrend.value.windows[selectedTrendWindowIndex.value];
  if (!point) return null;
  const start = new Date(point.window_start);
  const end = new Date(start.getTime() + vesselTrend.value.interval_hours * 3600 * 1000);
  return {
    index: selectedTrendWindowIndex.value,
    start: start.toISOString(),
    end: end.toISOString(),
    label: point.window_start.slice(5, 16).replace("T", " "),
    pointCount: point.point_count,
    meanSog: point.mean_sog,
    lowSpeedRatio: point.low_speed_ratio,
  };
});

const vesselStory = computed(() => {
  const historyTitle = vesselTrend.value
    ? `${vesselTrend.value.windows.length} 个历史窗口`
    : selectedVessel.value
      ? `${selectedVessel.value.track_duration_hours} 小时历史窗口`
      : "历史窗口";
  const historyDescription = vesselTrend.value
    ? trendSummary.value
    : "当前尚未加载到可用于判读的历史趋势。";

  const forecastTitle = forecastAvailable.value
    ? `下一窗口预计${riskLabelText(vesselForecast.value.predicted_risk_label)}`
    : "预测暂不可用";
  const forecastDescription = forecastAvailable.value
    ? `若延续最近 ${vesselForecast.value.history_windows} 个窗口的行为与环境暴露，下一 ${vesselForecast.value.window_hours} 小时的预测 FPI 为 ${vesselForecast.value.predicted_fpi}，对应 ${riskLabelText(vesselForecast.value.predicted_risk_label)}。`
    : vesselForecast.value?.unavailable_reason || "当前对象暂未生成连续预测结果。";

  return [
    {
      kicker: "历史",
      title: historyTitle,
      description: historyDescription,
    },
    {
      kicker: "预测",
      title: forecastTitle,
      description: forecastDescription,
    },
  ];
});

const focusTypeHint = computed(() => {
  if (!focusAnomalyType.value || !vesselAnomaly.value) return null;
  const sameType = vesselAnomaly.value.anomaly_type === focusAnomalyType.value;
  return sameType
    ? `当前页面从“${vesselAnomaly.value.anomaly_type_label}”视角进入，当前对象与所选类型一致。`
    : `当前页面从异常类型切片进入；所选类型为“${anomalyTypeLabel(focusAnomalyType.value)}”，当前对象实际属于“${vesselAnomaly.value.anomaly_type_label}”。`;
});

const forecastGauge = computed(() => {
  if (!vesselForecast.value || !forecastAvailable.value) return null;
  const totalWidth = 100;
  const clamp = (value) => Math.max(0, Math.min(totalWidth, value));
  const valueX = clamp(vesselForecast.value.predicted_fpi * totalWidth);
  const lowX = clamp(vesselForecast.value.low_threshold * totalWidth);
  const highX = clamp(vesselForecast.value.high_threshold * totalWidth);
  const bandLowX = clamp(vesselForecast.value.confidence_band_low * totalWidth);
  const bandHighX = clamp(vesselForecast.value.confidence_band_high * totalWidth);

  return {
    lowX,
    highX,
    valueX,
    bandLowX,
    bandHighX,
  };
});

const forecastHistorySvg = computed(() => {
  if (!vesselForecast.value || !forecastAvailable.value || !forecastHistoryPoints.value.length) return null;
  const width = 620;
  const height = 170;
  const paddingLeft = 18;
  const paddingRight = 18;
  const topPadding = 18;
  const bottomPadding = 34;
  const innerWidth = width - paddingLeft - paddingRight;
  const innerHeight = height - topPadding - bottomPadding;
  const history = forecastHistoryPoints.value;
  const values = history.map((item) => item.fpi_proxy);
  values.push(vesselForecast.value.predicted_fpi);
  const maxValue = Math.max(...values, vesselForecast.value.high_threshold, 0.8);
  const minValue = Math.min(...values, 0);

  const projectX = (index, total) =>
    total <= 1 ? width / 2 : paddingLeft + (index / (total - 1)) * innerWidth;
  const projectY = (value) => {
    const span = Math.max(maxValue - minValue, 0.12);
    const normalized = (value - minValue) / span;
    return topPadding + innerHeight - normalized * innerHeight;
  };

  const historyPath = history
    .map((item, index) => `${index === 0 ? "M" : "L"} ${projectX(index, history.length).toFixed(2)} ${projectY(item.fpi_proxy).toFixed(2)}`)
    .join(" ");

  const forecastX = projectX(history.length - 1, history.length) + (history.length > 1 ? innerWidth / (history.length - 1) : 0);
  const forecastY = projectY(vesselForecast.value.predicted_fpi);
  const thresholdLines = [
    { label: "Low/Medium", value: vesselForecast.value.low_threshold },
    { label: "Medium/High", value: vesselForecast.value.high_threshold },
  ];

  return {
    width,
    height,
    history,
    historyPath,
    forecastX,
    forecastY,
    paddingLeft,
    widthInnerEnd: width - paddingRight,
    thresholdLines: thresholdLines.map((item) => ({
      ...item,
      y: projectY(item.value),
    })),
    points: history.map((item, index) => ({
      label: item.window_start.slice(5, 16).replace("T", " "),
      x: projectX(index, history.length),
      y: projectY(item.fpi_proxy),
      value: item.fpi_proxy,
    })),
    lastHistoryPointX: history.length ? projectX(history.length - 1, history.length) : paddingLeft,
    lastHistoryPointY: history.length ? projectY(history[history.length - 1].fpi_proxy) : topPadding + innerHeight,
  };
});

const trendSummary = computed(() => {
  if (!vesselTrend.value?.windows?.length) return "";
  const lowSpeedValues = vesselTrend.value.windows.map((item) => item.low_speed_ratio ?? 0);
  const meanSogValues = vesselTrend.value.windows.map((item) => item.mean_sog ?? 0);
  const lowSpeedMean =
    lowSpeedValues.reduce((total, value) => total + value, 0) / Math.max(lowSpeedValues.length, 1);
  const speedMin = Math.min(...meanSogValues);
  const speedMax = Math.max(...meanSogValues);
  const pointTotal = vesselTrend.value.windows.reduce((total, item) => total + item.point_count, 0);
  return `当前共划分 ${vesselTrend.value.windows.length} 个历史窗口，累计 ${pointTotal} 个 AIS 点；平均航速在 ${speedMin.toFixed(3)} ~ ${speedMax.toFixed(3)} 节之间，低速停留均值约为 ${(lowSpeedMean * 100).toFixed(0)}%。`;
});

const svgTrend = computed(() => {
  if (!vesselTrend.value?.windows?.length) return null;

  const width = 920;
  const height = 360;
  const paddingLeft = 54;
  const paddingRight = 54;
  const topPadding = 24;
  const bottomPadding = 56;
  const innerWidth = width - paddingLeft - paddingRight;
  const innerHeight = height - topPadding - bottomPadding;
  const windows = vesselTrend.value.windows;
  const sogValues = windows.map((item) => item.mean_sog ?? 0);
  const ratioValues = windows.map((item) => item.low_speed_ratio ?? 0);
  const sogMinRaw = Math.min(...sogValues);
  const sogMaxRaw = Math.max(...sogValues);
  const ratioMinRaw = Math.min(...ratioValues);
  const ratioMaxRaw = Math.max(...ratioValues);
  const sogSpan = Math.max(sogMaxRaw - sogMinRaw, 0.08);
  const ratioSpan = Math.max(ratioMaxRaw - ratioMinRaw, 0.04);
  const sogPadding = Math.max(sogSpan * 0.8, 0.18);
  const ratioPadding = Math.max(ratioSpan * 0.8, 0.04);
  const sogMin = Math.max(0, sogMinRaw - sogPadding);
  const sogMax = sogMaxRaw + sogPadding;
  const ratioMin = Math.max(0, ratioMinRaw - ratioPadding);
  const ratioMax = ratioMaxRaw + ratioPadding;
  const maxPointCount = Math.max(vesselTrend.value.max_point_count || 1, 1);

  const projectX = (index) => {
    if (windows.length === 1) return width / 2;
    return paddingLeft + (index / (windows.length - 1)) * innerWidth;
  };

  const projectSogY = (value) =>
    topPadding + innerHeight - ((((value ?? sogMin) - sogMin) / Math.max(sogMax - sogMin, 0.01)) * innerHeight);
  const projectLowSpeedY = (value) =>
    topPadding + innerHeight - ((((value ?? ratioMin) - ratioMin) / Math.max(ratioMax - ratioMin, 0.01)) * innerHeight);

  const speedPath = windows
    .map((item, index) => `${index === 0 ? "M" : "L"} ${projectX(index).toFixed(2)} ${projectSogY(item.mean_sog).toFixed(2)}`)
    .join(" ");

  const lowSpeedPath = windows
    .map((item, index) => `${index === 0 ? "M" : "L"} ${projectX(index).toFixed(2)} ${projectLowSpeedY(item.low_speed_ratio).toFixed(2)}`)
    .join(" ");

  const bars = windows.map((item, index) => {
    const x = projectX(index) - 12;
    const barHeight = ((item.point_count || 0) / maxPointCount) * innerHeight;
    return {
      label: item.window_start.slice(5, 16).replace("T", " "),
      x,
      y: topPadding + innerHeight - barHeight,
      width: 24,
      height: barHeight,
      cx: projectX(index),
      sogY: projectSogY(item.mean_sog),
      lowSpeedY: projectLowSpeedY(item.low_speed_ratio),
    };
  });

  const speedAxis = [sogMin, (sogMin + sogMax) / 2, sogMax].map((value) => ({
    value: value.toFixed(3),
    y: projectSogY(value),
  }));

  const ratioAxis = [ratioMin, (ratioMin + ratioMax) / 2, ratioMax].map((value) => ({
    value: `${Math.round(Math.min(Math.max(value, 0), 1) * 100)}%`,
    y: projectLowSpeedY(value),
  }));

  return {
    width,
    height,
    bars,
    speedPath,
    lowSpeedPath,
    speedAxis,
    ratioAxis,
    paddingLeft,
    paddingRight,
  };
});

function onSelectMmsi(event) {
  const nextValue = event.target.value;
  if (!nextValue || nextValue === route.params.mmsi) return;
  router.push(`/vessels/${nextValue}`);
}

function onSelectTrendWindow(index) {
  if (selectedTrendWindowIndex.value === index) {
    selectedTrendWindowIndex.value = null;
    return;
  }
  selectedTrendWindowIndex.value = index;
}

async function loadPageData() {
  pageError.value = "";
  trackError.value = "";
  trendError.value = "";
  forecastError.value = "";
  anomalyError.value = "";
  vesselTrack.value = null;
  vesselTrend.value = null;
  vesselForecast.value = null;
  vesselAnomaly.value = null;
  selectedTrendWindowIndex.value = null;

  try {
    await fetchDemoData();
    const mmsi = route.params.mmsi ? String(route.params.mmsi) : summary.value?.top_vessel?.mmsi;
    if (!mmsi) {
      throw new Error("当前没有可用的单船详情数据。");
    }

    selectedMmsi.value = mmsi;
    vesselDetail.value = await fetchVesselDetail(mmsi);
    reportPreview.value = await fetchVesselReportPreview(mmsi);

    try {
      vesselTrack.value = await fetchVesselTrack(mmsi);
    } catch (trackLoadError) {
      trackError.value = trackLoadError instanceof Error ? trackLoadError.message : "轨迹数据加载失败";
    }

    try {
      vesselTrend.value = await fetchVesselTrend(mmsi);
    } catch (trendLoadError) {
      trendError.value = trendLoadError instanceof Error ? trendLoadError.message : "趋势数据加载失败";
    }

    try {
      vesselForecast.value = await fetchVesselForecast(mmsi);
    } catch (forecastLoadError) {
      forecastError.value = forecastLoadError instanceof Error ? forecastLoadError.message : "预测数据加载失败";
    }

    try {
      vesselAnomaly.value = await fetchVesselAnomaly(mmsi);
    } catch (anomalyLoadError) {
      anomalyError.value = anomalyLoadError instanceof Error ? anomalyLoadError.message : "异常检测数据加载失败";
    }
  } catch (errorObject) {
    pageError.value = errorObject instanceof Error ? errorObject.message : "单船详情加载失败";
  }
}

onMounted(loadPageData);

watch(
  () => route.params.mmsi,
  () => {
    loadPageData();
  },
);
</script>

<template>
  <section v-if="(loading && !vesselDetail) || (!vesselDetail && !pageError && !error)" class="page-card empty-state">
    正在加载单船详情...
  </section>

  <section v-else-if="pageError || (error && !vesselDetail)" class="page-card empty-state error-state">
    {{ pageError || error }}
  </section>

  <template v-else-if="selectedVessel && vesselDetail">
    <section class="page-card selector-card">
      <label class="selector-label" for="mmsi-select">
        查看对象
        <HintTooltip text="按综合风险优先级排序，可直接切换查看不同 MMSI 的单船详情。" />
      </label>
      <select id="mmsi-select" class="selector-input" :value="selectedMmsi" @change="onSelectMmsi">
        <option v-for="item in vesselOptions" :key="item.value" :value="item.value">
          {{ item.label }}
        </option>
      </select>
    </section>

    <section class="hero-grid">
      <article class="page-card hero-copy-card">
        <p class="section-kicker">Vessel Detail</p>
        <h2>单船暴露诊断与 AIS 轨迹判读</h2>
        <div class="hero-capability-list">
          <div v-for="item in vesselHeroHighlights" :key="item.title" class="hero-capability-chip">
            <strong>{{ item.title }}</strong>
            <span>{{ item.description }}</span>
          </div>
        </div>
      </article>

      <article class="page-card summary-stack">
        <div class="summary-metric">
          <span>当前 MMSI</span>
          <strong>{{ selectedVessel.mmsi }}</strong>
        </div>
        <div class="summary-metric">
          <span>风险排位</span>
          <strong>{{ vesselDetail.rank_fraction }}</strong>
        </div>
        <div class="summary-metric">
          <span>FPI 代理值</span>
          <strong>{{ selectedVessel.fpi_proxy }}</strong>
        </div>
        <div class="summary-metric">
          <span>当前建议</span>
          <strong>{{ selectedVessel.recommendation }}</strong>
        </div>
      </article>
    </section>

    <section v-if="focusTypeHint" class="page-card compact-note-card">
      <p>{{ focusTypeHint }}</p>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Storyline</p>
        <h3>
          历史-预测链路
          <HintTooltip text="用同一页串联历史行为证据与下一时间窗预测结果，帮助快速判断对象后续走向。" />
        </h3>
      </div>
      <div class="storyline-grid">
        <article v-for="item in vesselStory" :key="item.kicker" class="page-card storyline-card">
          <p class="section-kicker">{{ item.kicker }}</p>
          <h4>{{ item.title }}</h4>
          <p>{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Anomaly</p>
        <h3>
          异常暴露解释
          <HintTooltip text="异常检测基于 Autoencoder 重建误差，判断该船的行为与环境暴露模式是否显著偏离同批对象。" />
        </h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card list-card">
          <div class="module-head">
            <h4>异常概览</h4>
            <span v-if="anomalyHeadline" class="status-pill">{{ anomalyHeadline.label }}</span>
          </div>
          <div v-if="vesselAnomaly" class="anomaly-overview-grid">
            <div class="summary-metric">
              <span>异常分数</span>
              <strong>{{ vesselAnomaly.anomaly_score }}</strong>
            </div>
            <div class="summary-metric">
              <span>分位位置</span>
              <strong>前 {{ anomalyHeadline?.percentile }}</strong>
            </div>
            <div class="summary-metric">
              <span>异常类型</span>
              <strong>{{ vesselAnomaly.anomaly_type_label }}</strong>
            </div>
            <div class="summary-metric">
              <span>严重度</span>
              <strong>{{ vesselAnomaly.anomaly_severity }}</strong>
            </div>
          </div>
          <div v-if="vesselAnomaly?.dominant_evidence_title" class="list-row">
            <div>
              <strong>主导证据</strong>
              <span>{{ vesselAnomaly.dominant_evidence_title }} · {{ vesselAnomaly.dominant_evidence_summary }}</span>
            </div>
          </div>
          <div v-if="vesselAnomaly?.anomaly_type_summary" class="list-row">
            <div>
              <strong>类型说明</strong>
              <span>{{ vesselAnomaly.anomaly_type_summary }}</span>
            </div>
          </div>
          <div v-if="vesselAnomaly?.summary_sentence" class="list-row">
            <div>
              <strong>简要结论</strong>
              <span>{{ vesselAnomaly.summary_sentence }}</span>
            </div>
          </div>
          <div v-if="vesselAnomaly?.driver_details?.length" class="signal-chip-list">
            <div v-for="driver in vesselAnomaly.driver_details" :key="driver.feature_key" class="signal-chip">
              <strong>{{ driver.feature_label }}</strong>
              <span>
                当前值 {{ driver.vessel_value ?? "暂无" }} · 样本中位数 {{ driver.cohort_median ?? "暂无" }}
              </span>
              <small>{{ driver.interpretation }}</small>
            </div>
          </div>
          <div v-if="vesselAnomaly?.explanations?.length" class="signal-chip-list">
            <div v-for="item in vesselAnomaly.explanations" :key="item" class="signal-chip">
              <strong>异常驱动</strong>
              <span>{{ item }}</span>
            </div>
          </div>
          <div v-else class="list-row">
            <div>
              <strong>异常说明</strong>
              <span>{{ anomalyError || "当前没有可展示的异常解释。" }}</span>
            </div>
          </div>
        </article>

        <article class="page-card list-card">
          <div class="module-head">
            <h4>相邻异常对象</h4>
          </div>
          <RouterLink
            v-for="item in anomalyPeers"
            :key="item.mmsi"
            class="list-row link-row"
            :to="`/vessels/${item.mmsi}`"
          >
            <div>
              <strong>{{ item.mmsi }}</strong>
              <span>{{ item.anomaly_type_label || anomalyLevelLabel(item.anomaly_level) }} · {{ item.explanations[0] || "异常驱动待补充" }}</span>
            </div>
              <div class="list-metric">
                <div>#{{ item.rank }}</div>
                <div>Score {{ item.anomaly_score }}</div>
              </div>
            </RouterLink>
          <div v-if="!anomalyPeers.length" class="list-row">
            <div>
              <strong>异常邻近榜单</strong>
              <span>{{ anomalyError || "当前没有可展示的对比对象。" }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Forecast</p>
        <h3>
          下一时间窗 FPI 预测
          <HintTooltip text="预测基于最近 8 个 6 小时窗口的 AIS 行为序列与环境暴露序列，由当前最优 LSTM 模型输出。" />
        </h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card forecast-card">
          <div v-if="vesselForecast && forecastAvailable" class="forecast-stack">
            <div class="forecast-score-row">
              <div>
                <p class="forecast-label">预测 FPI</p>
                <strong class="forecast-score">{{ vesselForecast.predicted_fpi }}</strong>
              </div>
              <div>
                <p class="forecast-label">预测等级</p>
                <strong class="forecast-score">{{ riskLabelText(vesselForecast.predicted_risk_label) }}</strong>
              </div>
            </div>
            <div class="forecast-meta-grid">
              <div class="summary-metric">
                <span>预测窗口</span>
                <strong>{{ vesselForecast.forecast_window_start }} -> {{ vesselForecast.forecast_window_end }}</strong>
              </div>
              <div class="summary-metric">
                <span>预测区间</span>
                <strong>{{ vesselForecast.confidence_band_low }} ~ {{ vesselForecast.confidence_band_high }}</strong>
              </div>
              <div class="summary-metric">
                <span>模型校准准确率</span>
                <strong>{{ vesselForecast.calibrated_accuracy ?? "暂无" }}</strong>
              </div>
              <div class="summary-metric">
                <span>验证集 RMSE</span>
                <strong>{{ vesselForecast.validation_rmse ?? "暂无" }}</strong>
              </div>
            </div>
            <div v-if="forecastGauge" class="forecast-gauge-card">
              <div class="forecast-gauge-track">
                <div class="forecast-band forecast-band--low" :style="{ left: '0%', width: `${forecastGauge.lowX}%` }"></div>
                <div
                  class="forecast-band forecast-band--medium"
                  :style="{ left: `${forecastGauge.lowX}%`, width: `${forecastGauge.highX - forecastGauge.lowX}%` }"
                ></div>
                <div
                  class="forecast-band forecast-band--high"
                  :style="{ left: `${forecastGauge.highX}%`, width: `${100 - forecastGauge.highX}%` }"
                ></div>
                <div
                  class="forecast-confidence-band"
                  :style="{ left: `${forecastGauge.bandLowX}%`, width: `${forecastGauge.bandHighX - forecastGauge.bandLowX}%` }"
                ></div>
                <div class="forecast-marker" :style="{ left: `${forecastGauge.valueX}%` }"></div>
              </div>
              <div class="forecast-gauge-labels">
                <span>低风险</span>
                <span>中风险</span>
                <span>高风险</span>
              </div>
            </div>
            <div v-if="forecastHistorySvg" class="forecast-history-card">
              <svg
                :viewBox="`0 0 ${forecastHistorySvg.width} ${forecastHistorySvg.height}`"
                class="forecast-history-svg"
                role="img"
                aria-label="近期 FPI 历史与下一时间窗预测"
              >
                <rect x="0" y="0" :width="forecastHistorySvg.width" :height="forecastHistorySvg.height" rx="18" class="trend-bg" />
                <line
                  v-for="line in forecastHistorySvg.thresholdLines"
                  :key="line.label"
                  :x1="forecastHistorySvg.paddingLeft"
                  :x2="forecastHistorySvg.widthInnerEnd"
                  :y1="line.y"
                  :y2="line.y"
                  class="forecast-threshold-line"
                />
                <path :d="forecastHistorySvg.historyPath" class="forecast-history-line" />
                <circle
                  v-for="point in forecastHistorySvg.points"
                  :key="point.label"
                  :cx="point.x"
                  :cy="point.y"
                  r="4.5"
                  class="forecast-history-dot"
                />
                <line
                  :x1="forecastHistorySvg.lastHistoryPointX"
                  :y1="forecastHistorySvg.lastHistoryPointY"
                  :x2="forecastHistorySvg.forecastX"
                  :y2="forecastHistorySvg.forecastY"
                  class="forecast-projection-line"
                />
                <circle :cx="forecastHistorySvg.forecastX" :cy="forecastHistorySvg.forecastY" r="7" class="forecast-point-dot" />
              </svg>
              <div class="forecast-history-labels">
                <span v-for="point in forecastHistorySvg.points" :key="point.label">{{ point.label }}</span>
                <span>预测</span>
              </div>
            </div>
          </div>
          <div v-else-if="vesselForecast" class="empty-state track-empty">
            {{ vesselForecast.unavailable_reason || "当前对象暂未生成预测结果。" }}
          </div>
          <div v-else class="empty-state track-empty">
            {{ forecastError || "当前没有可展示的预测结果。" }}
          </div>
        </article>

        <article class="page-card list-card">
          <div class="module-head">
            <h4>预测解释</h4>
          </div>
          <div v-if="vesselForecast && forecastAvailable" class="list-row">
            <div>
              <strong>模型口径</strong>
              <span>当前使用 {{ vesselForecast.model_name }}，最近 {{ vesselForecast.history_windows }} 个窗口预测未来 {{ vesselForecast.window_hours }} 小时。</span>
            </div>
          </div>
          <div v-if="vesselForecast && forecastAvailable" class="list-row">
            <div>
              <strong>等级校准</strong>
              <span>校准阈值为 low / medium {{ vesselForecast.low_threshold }}，medium / high {{ vesselForecast.high_threshold }}。</span>
            </div>
          </div>
          <div v-if="vesselForecast && forecastAvailable" class="signal-chip-list">
            <div v-for="signal in forecastSignals" :key="signal.title" class="signal-chip">
              <strong>{{ signal.title }}</strong>
              <span>{{ signal.value }} · {{ signal.assessment }}</span>
              <small>{{ signal.detail }}</small>
            </div>
          </div>
          <div v-else-if="vesselForecast" class="list-row">
            <div>
              <strong>未生成原因</strong>
              <span>{{ vesselForecast.unavailable_reason }}</span>
            </div>
          </div>
          <div v-else class="list-row">
            <div>
              <strong>预测状态</strong>
              <span>{{ forecastError || "预测模块尚未返回数据。" }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Track Map</p>
        <h3>
          AIS 轨迹地图
          <HintTooltip text="轨迹基于真实 AIS 点绘制，起点、终点、低速点与最近港口/锚地参考点叠加在同一底图中。" />
        </h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card map-panel-card">
          <VesselTrackMap :track="vesselTrack" :nearest-reference="nearestReference" :highlighted-window="selectedTrendWindow" />
        </article>
        <article class="page-card list-card">
          <div class="module-head">
            <h4>轨迹说明</h4>
          </div>
          <div v-if="selectedTrendWindow" class="list-row">
            <div>
              <strong>联动时间窗</strong>
              <span>
                当前高亮 {{ selectedTrendWindow.label }}，共 {{ selectedTrendWindow.pointCount }} 个轨迹点，
                平均航速 {{ selectedTrendWindow.meanSog ?? "暂无" }}，低速比例 {{ selectedTrendWindow.lowSpeedRatio ?? "暂无" }}。
              </span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>交互开关</strong>
              <span>可切换主轨迹、近 24 小时轨迹、低速点和参考点，并可一键回到全轨迹视角；若选中趋势分窗，地图会同步高亮对应轨迹段。</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>起点 / 终点</strong>
              <span>绿色表示起点，橙色表示终点。</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>低速位置</strong>
              <span>浅色点表示低速活动位置抽样，用于辅助识别停留与等待区。</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>参考点</strong>
              <span>若存在匹配，将显示最近港口或锚地参考点。</span>
            </div>
          </div>
          <div v-if="trackError" class="list-row">
            <div>
              <strong>轨迹状态</strong>
              <span>{{ trackError }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="page-card compact-note-card">
      <p>{{ compactSummary }}</p>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Trend</p>
        <h3>
          时间趋势
          <HintTooltip text="左轴为平均航速，右轴为低速比例，柱体表示每个时间窗内的轨迹点数量。" />
        </h3>
      </div>
      <article class="page-card trend-card">
        <div class="module-head">
          <h4>{{ vesselTrend ? `${vesselTrend.interval_hours} 小时分窗趋势` : "时间趋势图" }}</h4>
          <div class="trend-head-actions">
            <span class="status-pill" v-if="vesselTrend">真实分窗</span>
            <button v-if="selectedTrendWindow" type="button" class="trend-reset-button" @click="selectedTrendWindowIndex = null">清除联动</button>
          </div>
        </div>
        <div v-if="svgTrend" class="trend-stage">
          <svg :viewBox="`0 0 ${svgTrend.width} ${svgTrend.height}`" class="trend-svg" role="img" aria-label="单船时间趋势图">
            <rect x="0" y="0" :width="svgTrend.width" :height="svgTrend.height" rx="18" class="trend-bg" />
            <line
              v-for="axis in svgTrend.speedAxis"
              :key="`speed-axis-${axis.value}`"
              :x1="svgTrend.paddingLeft"
              :x2="svgTrend.width - svgTrend.paddingRight"
              :y1="axis.y"
              :y2="axis.y"
              class="trend-grid-line"
            />
            <text
              v-for="axis in svgTrend.speedAxis"
              :key="`speed-label-${axis.value}`"
              :x="10"
              :y="axis.y + 4"
              class="trend-axis-label"
            >
              {{ axis.value }}
            </text>
            <text
              v-for="axis in svgTrend.ratioAxis"
              :key="`ratio-label-${axis.value}`"
              :x="svgTrend.width - 42"
              :y="axis.y + 4"
              class="trend-axis-label"
            >
              {{ axis.value }}
            </text>
            <rect
              v-for="(bar, index) in svgTrend.bars"
              :key="`bar-${bar.label}`"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
              rx="6"
              class="trend-bar"
              :class="{ 'trend-bar--active': selectedTrendWindowIndex === index }"
              @click="onSelectTrendWindow(index)"
            />
            <path :d="svgTrend.speedPath" class="trend-speed-line" />
            <path :d="svgTrend.lowSpeedPath" class="trend-low-line" />
            <circle
              v-for="(bar, index) in svgTrend.bars"
              :key="`speed-${bar.label}`"
              :cx="bar.cx"
              :cy="bar.sogY"
              r="4"
              class="trend-speed-dot"
              @click="onSelectTrendWindow(index)"
            />
            <circle
              v-for="(bar, index) in svgTrend.bars"
              :key="`slow-${bar.label}`"
              :cx="bar.cx"
              :cy="bar.lowSpeedY"
              r="4"
              class="trend-low-dot"
              @click="onSelectTrendWindow(index)"
            />
          </svg>
          <div class="trend-labels">
            <button
              v-for="(bar, index) in svgTrend.bars"
              :key="bar.label"
              type="button"
              class="trend-label-button"
              :class="{ active: selectedTrendWindowIndex === index }"
              @click="onSelectTrendWindow(index)"
            >
              {{ bar.label }}
            </button>
          </div>
          <div class="trend-legend">
            <span><i class="legend-swatch legend-swatch--bar"></i> 轨迹点数</span>
            <span><i class="legend-swatch legend-swatch--speed"></i> 平均航速</span>
            <span><i class="legend-swatch legend-swatch--slow"></i> 低速比例</span>
          </div>
          <p class="trend-note">{{ trendSummary }}</p>
        </div>
        <div v-else class="empty-state track-empty">
          {{ trendError || "当前没有可展示的趋势数据。" }}
        </div>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Signals</p>
        <h3>
          单船关键字段
          <HintTooltip text="相对高低基于当前样本内的相对分布，不是外部绝对阈值。" />
        </h3>
      </div>
      <div class="card-grid">
        <article v-for="item in vesselFacts" :key="item.title" class="page-card module-card">
          <div class="module-head">
            <h4>{{ item.title }}</h4>
            <span v-if="item.assessment" class="status-pill">{{ item.assessment }}</span>
          </div>
          <p class="feature-highlight small">{{ item.value }}</p>
          <p>{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Profile</p>
        <h3>船舶画像</h3>
      </div>
      <div class="card-grid">
        <article v-for="item in staticFacts" :key="item.title" class="page-card module-card">
          <div class="module-head">
            <h4>{{ item.title }}</h4>
          </div>
          <p class="feature-highlight small">{{ item.value }}</p>
          <p>{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Validation</p>
        <h3>外部校验摘要</h3>
      </div>
      <div class="card-grid">
        <article v-for="item in validationFacts" :key="item.title" class="page-card module-card">
          <div class="module-head">
            <h4>{{ item.title }}</h4>
          </div>
          <p class="feature-highlight small">{{ item.value }}</p>
          <p>{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Report</p>
        <h3>单船报告预览</h3>
      </div>
      <article class="page-card text-card">
        <p v-for="line in reportPreview?.lines || []" :key="line">{{ line }}</p>
      </article>
    </section>
  </template>
</template>
