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

const layerOptions = [
  { key: "rri_score", title: "综合风险", shortLabel: "RRI" },
  { key: "traffic_score", title: "交通疏密", shortLabel: "交通" },
  { key: "low_speed_score", title: "低速停留", shortLabel: "停留" },
  { key: "environment_score", title: "水域情况", shortLabel: "水域" },
];

const topVessels = computed(() => vessels.value.slice(0, 8));
const referenceSites = computed(() => regionalStats.value?.reference_sites || []);
const layerMeta = computed(() => layerOptions.find((item) => item.key === activeLayer.value) || layerOptions[0]);
const anomalyCounts = computed(() => anomalySummary.value?.anomaly_level_counts || {});
const anomalyTypeCounts = computed(() => anomalySummary.value?.anomaly_type_counts || {});
const topAnomalies = computed(() => anomalySummary.value?.top_anomalies || []);

const sortedCells = computed(() =>
  [...riskCells.value]
    .filter((cell) => cell[activeLayer.value] !== null && cell[activeLayer.value] !== undefined)
    .sort((left, right) => (right[activeLayer.value] || 0) - (left[activeLayer.value] || 0)),
);

const topCells = computed(() => sortedCells.value.slice(0, 8));

const selectedHotspot = computed(() => {
  if (!sortedCells.value.length) return null;
  if (!selectedHotspotKey.value) return sortedCells.value[0];
  return sortedCells.value.find((item) => `${item.grid_lat}-${item.grid_lon}` === selectedHotspotKey.value) || sortedCells.value[0];
});

const hotspotSummary = computed(() => {
  const cell = selectedHotspot.value;
  if (!cell) return [];
  return [
    { label: "综合风险", value: cell.rri_score },
    { label: "交通疏密", value: cell.traffic_score },
    { label: "低速停留", value: cell.low_speed_score },
    { label: "水域情况", value: cell.environment_score },
  ];
});

function selectLayer(layerKey) {
  activeLayer.value = layerKey;
  if (sortedCells.value.length) {
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
        <p class="support-text">
          平台基于 AIS 航迹与海洋环境数据，对研究区内空间热点、重点船舶和维护优先级进行统一展示。
        </p>
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
        <p>代表当前时间窗内风险水平最高的空间热点。</p>
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
        <p>暴露模式与同批对象差异最大的那一批船。</p>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Spatial View</p>
        <h3>
          区域主地图
          <HintTooltip text="地图用于识别空间风险，并区分热点主要由交通疏密、低速停留或水域情况驱动。" />
        </h3>
      </div>
      <div class="split-grid detail-layout dashboard-map-layout">
        <article class="page-card map-panel-card">
          <RiskOverviewMap
            :cells="riskCells"
            :active-layer="activeLayer"
            :selected-hotspot-key="selectedHotspotKey"
            :reference-sites="referenceSites"
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
                </span>
              </div>
              <div class="list-metric">
                <div>{{ layerMeta.shortLabel }} {{ selectedHotspot[activeLayer] }}</div>
                <div>RRI {{ selectedHotspot.rri_score }}</div>
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
                热点格网列表
                <HintTooltip text="列表与地图使用相同口径，切换视角后排序会同步更新。" />
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
                <span>{{ item.risk_level }} 风险，{{ item.vessel_count }} 艘船经过</span>
              </div>
              <div class="list-metric">
                <div>{{ layerMeta.shortLabel }} {{ item[activeLayer] }}</div>
                <div>{{ item.traffic_points }} 点</div>
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
            <div class="signal-chip">
              <strong>长时低速型</strong>
              <span>{{ anomalyTypeCounts.long_dwell_low_speed || 0 }} 艘</span>
            </div>
            <div class="signal-chip">
              <strong>高温高叶绿素型</strong>
              <span>{{ anomalyTypeCounts.warm_productive_water || 0 }} 艘</span>
            </div>
            <div class="signal-chip">
              <strong>混合异常型</strong>
              <span>{{ anomalyTypeCounts.mixed_anomaly || 0 }} 艘</span>
            </div>
            <div class="signal-chip">
              <strong>观测稀疏型</strong>
              <span>{{ anomalyTypeCounts.sparse_observation || 0 }} 艘</span>
            </div>
          </div>
        </article>

        <article class="page-card list-card">
          <div class="module-head">
            <h4>
              异常船舶榜单
              <HintTooltip text="点击后进入单船页，可继续查看简要结论、主要偏离项与轨迹表现。" />
            </h4>
          </div>
          <RouterLink
            v-for="item in topAnomalies"
            :key="item.mmsi"
            class="list-row link-row"
            :to="`/vessels/${item.mmsi}`"
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
