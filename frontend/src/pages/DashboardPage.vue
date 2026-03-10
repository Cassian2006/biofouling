<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import HintTooltip from "../components/HintTooltip.vue";
import RiskOverviewMap from "../components/RiskOverviewMap.vue";
import { useDemoData } from "../composables/useDemoData";

const {
  summary,
  vessels,
  riskCells,
  loading,
  error,
  fetchDemoData,
  fetchRegionalStats,
  fetchOverviewReportPreview,
  fetchAnomalySummary,
} = useDemoData();

const regionalStats = ref(null);
const overviewReport = ref(null);
const anomalySummary = ref(null);
const activeLayer = ref("rri_score");
const selectedHotspotKey = ref("");
const activeAnomalyType = ref("all");

const layerOptions = [
  { key: "rri_score", title: "综合风险", shortLabel: "总分" },
  { key: "traffic_score", title: "交通疏密", shortLabel: "交通" },
  { key: "low_speed_score", title: "低速停留", shortLabel: "停留" },
  { key: "environment_score", title: "水域情况", shortLabel: "水域" },
];

const overviewHighlights = [
  { title: "单船画像", description: "快速查看单船暴露结构、异常类型与维护建议。" },
  { title: "区域热点", description: "定位研究区内更值得优先审阅的空间格网。" },
  { title: "短期预测", description: "结合近期窗口序列判断下一时间窗的风险走向。" },
  { title: "异常筛查", description: "识别与常规样本差异更显著的船舶对象。" },
];

const topVessels = computed(() => vessels.value.slice(0, 8));
const referenceSites = computed(() => regionalStats.value?.reference_sites || []);
const layerMeta = computed(() => layerOptions.find((item) => item.key === activeLayer.value) || layerOptions[0]);
const anomalyCounts = computed(() => anomalySummary.value?.anomaly_level_counts || {});
const anomalyTypeCounts = computed(() => anomalySummary.value?.anomaly_type_counts || {});
const anomalyTypeProfiles = computed(() => anomalySummary.value?.anomaly_type_profiles || []);
const anomalyTypeSpatialSlices = computed(() => anomalySummary.value?.anomaly_type_spatial_slices || []);
const topAnomalies = computed(() => anomalySummary.value?.top_anomalies || []);
const filteredAnomalies = computed(() => {
  if (activeAnomalyType.value === "all") return topAnomalies.value;
  return topAnomalies.value.filter((item) => item.anomaly_type === activeAnomalyType.value);
});
const activeAnomalyProfile = computed(() => {
  if (activeAnomalyType.value === "all") return null;
  return anomalyTypeProfiles.value.find((item) => item.anomaly_type === activeAnomalyType.value) || null;
});
const activeSpatialSlice = computed(() => {
  if (activeAnomalyType.value === "all") return null;
  return anomalyTypeSpatialSlices.value.find((item) => item.anomaly_type === activeAnomalyType.value) || null;
});
const focusedHotspotKeys = computed(() => activeSpatialSlice.value?.top_hotspots.map((item) => item.grid_key) || []);

const sortedCells = computed(() =>
  [...riskCells.value]
    .filter((cell) => cell[activeLayer.value] !== null && cell[activeLayer.value] !== undefined)
    .sort((left, right) => (right[activeLayer.value] || 0) - (left[activeLayer.value] || 0)),
);

const topCells = computed(() => {
  if (!activeSpatialSlice.value) return sortedCells.value.slice(0, 8);
  const cellsByKey = new Map(riskCells.value.map((cell) => [`${cell.grid_lat}-${cell.grid_lon}`, cell]));
  return activeSpatialSlice.value.top_hotspots
    .map((item) => {
      const cell = cellsByKey.get(item.grid_key);
      return cell ? { ...cell, slice_vessel_count: item.vessel_count, slice_anomaly_score_mean: item.anomaly_score_mean } : null;
    })
    .filter(Boolean)
    .slice(0, 8);
});

const selectedHotspot = computed(() => {
  if (!sortedCells.value.length) return null;
  if (!selectedHotspotKey.value) return sortedCells.value[0];
  return sortedCells.value.find((item) => `${item.grid_lat}-${item.grid_lon}` === selectedHotspotKey.value) || sortedCells.value[0];
});

const hotspotSummary = computed(() => {
  const cell = selectedHotspot.value;
  if (!cell) return [];
  return [
    { label: "综合风险分值", value: cell.rri_score },
    { label: "交通疏密", value: cell.traffic_score },
    { label: "低速停留", value: cell.low_speed_score },
    { label: "水域情况", value: cell.environment_score },
  ];
});

const anomalyBaselineDescription =
  "这里的“正常均值”来自当前时间窗内 anomaly_level = normal 且观测充分的船舶样本，用作对照基线。";

function formatMetricDifference(metric) {
  if (metric.delta === null || metric.delta === undefined || metric.normal_mean === null || metric.normal_mean === undefined) {
    return "当前缺少可比基线";
  }
  if (Math.abs(metric.normal_mean) < 0.0001) {
    return metric.direction === "flat" ? "与正常样本接近" : `较正常样本偏移 ${metric.delta}`;
  }
  const percent = Math.abs((metric.delta / metric.normal_mean) * 100);
  if (percent < 2 || metric.direction === "flat") {
    return "与正常均值接近";
  }
  return metric.direction === "higher"
    ? `超出正常均值 ${percent.toFixed(0)}%`
    : `低于正常均值 ${percent.toFixed(0)}%`;
}

function selectLayer(layerKey) {
  activeLayer.value = layerKey;
  if (activeSpatialSlice.value?.top_hotspots?.length) {
    selectedHotspotKey.value = activeSpatialSlice.value.top_hotspots[0].grid_key;
  } else if (sortedCells.value.length) {
    selectedHotspotKey.value = `${sortedCells.value[0].grid_lat}-${sortedCells.value[0].grid_lon}`;
  }
}

function selectHotspot(keyOrCell) {
  if (typeof keyOrCell === "string") {
    selectedHotspotKey.value = keyOrCell;
    return;
  }
  selectedHotspotKey.value = `${keyOrCell.grid_lat}-${keyOrCell.grid_lon}`;
}

function levelLabel(level) {
  if (level === "highly_abnormal") return "高度异常";
  if (level === "suspicious") return "需复核";
  if (level === "observation_insufficient") return "观测不足";
  return "正常";
}

function selectAnomalyType(typeKey) {
  activeAnomalyType.value = activeAnomalyType.value === typeKey ? "all" : typeKey;
  if (activeAnomalyType.value === "all") {
    if (sortedCells.value.length) {
      selectedHotspotKey.value = `${sortedCells.value[0].grid_lat}-${sortedCells.value[0].grid_lon}`;
    }
    return;
  }
  const slice = anomalyTypeSpatialSlices.value.find((item) => item.anomaly_type === activeAnomalyType.value);
  if (slice?.top_hotspots?.length) {
    selectedHotspotKey.value = slice.top_hotspots[0].grid_key;
  }
}

function vesselLinkTarget(mmsi) {
  return activeAnomalyType.value === "all"
    ? `/vessels/${mmsi}`
    : { path: `/vessels/${mmsi}`, query: { anomalyType: activeAnomalyType.value } };
}

onMounted(async () => {
  try {
    await fetchDemoData();
    regionalStats.value = await fetchRegionalStats();
    overviewReport.value = await fetchOverviewReportPreview();
    anomalySummary.value = await fetchAnomalySummary();
    if (sortedCells.value.length) {
      selectedHotspotKey.value = `${sortedCells.value[0].grid_lat}-${sortedCells.value[0].grid_lon}`;
    }
  } catch {
    // Shared state already handles rendering.
  }
});
</script>

<template>
  <section v-if="loading && !summary" class="page-card empty-state">
    正在加载总览数据...
  </section>

  <section v-else-if="error && !summary" class="page-card empty-state error-state">
    {{ error }}
  </section>

  <template v-else-if="summary && regionalStats">
    <section class="hero-grid">
      <article class="page-card hero-copy-card">
        <p class="section-kicker">Overview</p>
        <h2>新加坡海峡船舶生物污损风险总览</h2>
        <div class="hero-capability-list">
          <div v-for="item in overviewHighlights" :key="item.title" class="hero-capability-chip">
            <strong>{{ item.title }}</strong>
            <span>{{ item.description }}</span>
          </div>
        </div>
      </article>

      <article class="page-card summary-stack">
        <div class="summary-metric">
          <span>分析时间窗</span>
          <strong>{{ summary.window_label }}</strong>
        </div>
        <div class="summary-metric">
          <span>纳入分析船舶</span>
          <strong>{{ summary.vessels_summarized }}</strong>
        </div>
        <div class="summary-metric">
          <span>区域格网单元</span>
          <strong>{{ summary.grid_cells }}</strong>
        </div>
        <div class="summary-metric">
          <span>
            最高优先级船舶
            <HintTooltip text="指当前样本中综合风险排序最高、建议优先审阅的船舶对象。" />
          </span>
          <strong>{{ summary.top_vessel.mmsi }}</strong>
        </div>
      </article>
    </section>

    <section class="stats-grid">
      <article class="page-card stat-card">
        <span class="stat-label">高风险格网</span>
        <strong class="stat-value">{{ summary.high_risk_cells }}</strong>
        <p>当前时间窗内风险水平最高的空间热点。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">中风险格网</span>
        <strong class="stat-value">{{ summary.medium_risk_cells }}</strong>
        <p>代表需要持续跟踪的区域。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">优先评估清洗</span>
        <strong class="stat-value">{{ summary.recommendation_counts["Prioritize cleaning assessment"] || 0 }}</strong>
        <p>建议优先纳入维护评估的船舶数量。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">高度异常船舶</span>
        <strong class="stat-value">{{ anomalyCounts.highly_abnormal || 0 }}</strong>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Spatial View</p>
        <h3>
          区域主地图
          <HintTooltip text="地图用于识别空间风险，并区分热点主要由交通疏密、低速停留或水域情况驱动。综合风险分值表示该格网的总体风险水平。" />
        </h3>
      </div>
      <div class="split-grid detail-layout dashboard-map-layout">
        <article class="page-card map-panel-card">
          <RiskOverviewMap
            :cells="riskCells"
            :active-layer="activeLayer"
            :selected-hotspot-key="selectedHotspotKey"
            :reference-sites="referenceSites"
            :focused-hotspot-keys="focusedHotspotKeys"
            :focused-hotspot-label="activeSpatialSlice ? `${activeSpatialSlice.anomaly_type_label}空间热点` : ''"
            @select-hotspot="selectHotspot"
          />
        </article>

        <div class="dashboard-side-stack">
          <article class="page-card layer-switch-card">
            <button
              v-for="item in layerOptions"
              :key="item.key"
              type="button"
              class="layer-chip"
              :class="{ active: item.key === activeLayer }"
              @click="selectLayer(item.key)"
            >
              <strong>{{ item.title }}</strong>
              <span>按 {{ item.shortLabel }} 视角查看</span>
            </button>
          </article>

          <article v-if="activeSpatialSlice" class="page-card list-card">
            <div class="module-head">
              <h4>
                类型空间热点
                <HintTooltip text="选择异常类型后，地图会强调该类型船舶更集中出现的热点格网，并让列表同步切换到对应空间区域。" />
              </h4>
              <span class="status-pill">{{ activeSpatialSlice.highlighted_cells }} 个格网</span>
            </div>
            <div class="list-row">
              <div>
                <strong>{{ activeSpatialSlice.anomaly_type_label }}</strong>
                <span>{{ activeSpatialSlice.summary }}</span>
              </div>
            </div>
          </article>

          <article v-if="selectedHotspot" class="page-card list-card">
            <div class="module-head">
              <h4>
                当前热点格网
                <HintTooltip text="热点说明会随图层切换而变化，点击地图或列表中的格网即可切换。" />
              </h4>
            </div>
            <div class="list-row">
              <div>
                <strong>{{ selectedHotspot.grid_lat }}, {{ selectedHotspot.grid_lon }}</strong>
                <span>
                  {{ selectedHotspot.risk_level }} 风险，{{ selectedHotspot.vessel_count }} 艘船经过，
                  最近参考点 {{ selectedHotspot.nearest_reference_name || "暂无" }}
                  <template v-if="activeSpatialSlice && focusedHotspotKeys.includes(`${selectedHotspot.grid_lat}-${selectedHotspot.grid_lon}`)">
                    ，该格网属于当前异常类型的重点空间区域
                  </template>
                </span>
              </div>
              <div class="list-metric">
                <div>{{ layerMeta.shortLabel }} {{ selectedHotspot[activeLayer] }}</div>
                <div>综合风险分值 {{ selectedHotspot.rri_score }}</div>
              </div>
            </div>
            <div v-for="item in hotspotSummary" :key="item.label" class="list-row hotspot-row">
              <div>
                <strong>{{ item.label }}</strong>
              </div>
              <div class="list-metric">{{ item.value }}</div>
            </div>
          </article>

          <article class="page-card list-card">
            <div class="module-head">
              <h4>
                {{ activeSpatialSlice ? "类型热点格网列表" : "热点格网列表" }}
                <HintTooltip :text="activeSpatialSlice ? '当前列表已切换为所选异常类型更集中的热点格网。' : '列表与地图使用相同口径，切换视角后排序会同步更新。'" />
              </h4>
            </div>
            <button
              v-for="item in topCells"
              :key="`${item.grid_lat}-${item.grid_lon}`"
              type="button"
              class="list-row list-button"
              :class="{ active: `${item.grid_lat}-${item.grid_lon}` === selectedHotspotKey }"
              @click="selectHotspot(item)"
            >
              <div>
                <strong>{{ item.grid_lat }}, {{ item.grid_lon }}</strong>
                <span>
                  {{ item.risk_level }} 风险，{{ item.vessel_count }} 艘船经过
                  <template v-if="activeSpatialSlice && item.slice_vessel_count">
                    ，其中 {{ item.slice_vessel_count }} 艘属于当前异常类型
                  </template>
                </span>
              </div>
              <div class="list-metric">
                <div>{{ layerMeta.shortLabel }} {{ item[activeLayer] }}</div>
                <div v-if="activeSpatialSlice && item.slice_anomaly_score_mean !== undefined">异常均值 {{ item.slice_anomaly_score_mean }}</div>
                <div v-else>{{ item.traffic_points }} 点</div>
              </div>
            </button>
          </article>
        </div>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Anomaly</p>
        <h3>
          异常暴露筛查
          <HintTooltip text="用于识别暴露模式显著偏离样本基线的船舶对象。" />
        </h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card list-card">
          <div class="module-head">
            <h4>异常等级分布</h4>
          </div>
          <div class="anomaly-chip-row">
            <div class="anomaly-chip anomaly-chip--alert">
              <strong>{{ anomalyCounts.highly_abnormal || 0 }}</strong>
              <span>高度异常</span>
            </div>
            <div class="anomaly-chip anomaly-chip--warn">
              <strong>{{ anomalyCounts.suspicious || 0 }}</strong>
              <span>需复核</span>
            </div>
            <div class="anomaly-chip anomaly-chip--calm">
              <strong>{{ anomalyCounts.normal || 0 }}</strong>
              <span>正常</span>
            </div>
            <div class="anomaly-chip anomaly-chip--neutral">
              <strong>{{ anomalyCounts.observation_insufficient || 0 }}</strong>
              <span>观测不足</span>
            </div>
          </div>
          <p class="support-text anomaly-caption">
            观测不足对象不参与异常等级比较，避免短轨迹或低点数样本误占异常榜。
          </p>
          <div class="signal-chip-list anomaly-type-grid">
            <button type="button" class="signal-chip signal-chip--button" :class="{ active: activeAnomalyType === 'long_dwell_low_speed' }" @click="selectAnomalyType('long_dwell_low_speed')">
              <strong>长时低速型</strong>
              <span>{{ anomalyTypeCounts.long_dwell_low_speed || 0 }} 艘</span>
            </button>
            <button type="button" class="signal-chip signal-chip--button" :class="{ active: activeAnomalyType === 'warm_productive_water' }" @click="selectAnomalyType('warm_productive_water')">
              <strong>高温高叶绿素型</strong>
              <span>{{ anomalyTypeCounts.warm_productive_water || 0 }} 艘</span>
            </button>
            <button type="button" class="signal-chip signal-chip--button" :class="{ active: activeAnomalyType === 'mixed_anomaly' }" @click="selectAnomalyType('mixed_anomaly')">
              <strong>混合异常型</strong>
              <span>{{ anomalyTypeCounts.mixed_anomaly || 0 }} 艘</span>
            </button>
            <button type="button" class="signal-chip signal-chip--button" :class="{ active: activeAnomalyType === 'sparse_observation' }" @click="selectAnomalyType('sparse_observation')">
              <strong>观测稀疏型</strong>
              <span>{{ anomalyTypeCounts.sparse_observation || 0 }} 艘</span>
            </button>
          </div>
        </article>

        <article class="page-card list-card">
          <div class="module-head">
            <h4>
              异常船舶榜单
              <HintTooltip text="点击后进入单船页，可继续查看简要结论、主要偏离项与轨迹表现。" />
            </h4>
            <span v-if="activeAnomalyProfile" class="status-pill">{{ activeAnomalyProfile.anomaly_type_label }}</span>
          </div>
          <div v-if="activeAnomalyProfile" class="list-row">
            <div>
              <strong>当前切片</strong>
              <span>{{ activeAnomalyProfile.summary }}</span>
            </div>
          </div>
          <RouterLink
            v-for="item in filteredAnomalies"
            :key="item.mmsi"
            class="list-row link-row"
            :to="vesselLinkTarget(item.mmsi)"
          >
            <div>
              <strong>{{ item.mmsi }}</strong>
              <span>{{ item.summary_sentence || `${levelLabel(item.anomaly_level)} · ${item.explanations[0] || "异常驱动待补充"}` }}</span>
              <span>{{ item.anomaly_type_label || "异常类型待识别" }} · 严重度 {{ item.anomaly_severity || "待定" }}{{ item.dominant_evidence ? ` · ${item.dominant_evidence}` : "" }}</span>
            </div>
            <div class="list-metric">
              <div>#{{ item.rank }}</div>
              <div>Score {{ item.anomaly_score }}</div>
            </div>
          </RouterLink>
          <div v-if="!filteredAnomalies.length" class="list-row">
            <div>
              <strong>当前切片暂无对象</strong>
              <span>可以切换到其他异常类型，或再次点击当前标签返回全部对象。</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Type Compare</p>
        <h3>
          异常类型对比
          <HintTooltip text="将各类异常对象与正常船舶做对比，帮助理解每类异常最突出的偏离指标。" />
        </h3>
        <p class="support-text">{{ anomalyBaselineDescription }}</p>
      </div>
      <div class="card-grid anomaly-profile-grid">
        <article
          v-for="profile in anomalyTypeProfiles"
          :key="profile.anomaly_type"
          class="page-card module-card anomaly-profile-card"
          :class="{ active: activeAnomalyType === profile.anomaly_type }"
          @click="selectAnomalyType(profile.anomaly_type)"
        >
          <div class="module-head">
            <h4>{{ profile.anomaly_type_label }}</h4>
            <span class="status-pill">{{ profile.vessel_count }} 艘</span>
          </div>
          <p>{{ profile.summary }}</p>
          <div class="signal-chip-list">
            <div v-for="metric in profile.key_metrics" :key="metric.metric_key" class="signal-chip">
              <strong>{{ metric.metric_label }}</strong>
              <span>类型均值 {{ metric.type_mean ?? "暂无" }} · 正常均值 {{ metric.normal_mean ?? "暂无" }}</span>
              <small>{{ formatMetricDifference(metric) }}</small>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Visuals</p>
        <h3>可视化摘要</h3>
      </div>
      <div class="split-grid">
        <article class="page-card image-card">
          <img src="/demo/recommendation_breakdown.png" alt="船舶建议分布图" />
        </article>
        <article class="page-card image-card">
          <img src="/demo/top_vessels_fpi.png" alt="高风险船舶图" />
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Vessels</p>
        <h3>
          重点船舶列表
          <HintTooltip text="按综合风险排序，点击后进入单船详情页。" />
        </h3>
      </div>
      <article class="page-card list-card">
        <RouterLink
          v-for="item in topVessels"
          :key="item.mmsi"
          class="list-row link-row"
          :to="`/vessels/${item.mmsi}`"
        >
          <div>
            <strong>{{ item.mmsi }}</strong>
            <span>{{ item.recommendation }}</span>
          </div>
          <div class="list-metric">
            <div>FPI {{ item.fpi_proxy }}</div>
            <div>ECP {{ item.ecp_proxy }}</div>
          </div>
        </RouterLink>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Report</p>
        <h3>总览报告预览</h3>
      </div>
      <article class="page-card text-card">
        <p v-for="line in overviewReport?.lines || []" :key="line">{{ line }}</p>
      </article>
    </section>
  </template>
</template>
