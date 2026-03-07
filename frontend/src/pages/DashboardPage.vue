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
} = useDemoData();

const regionalStats = ref(null);
const overviewReport = ref(null);
const activeLayer = ref("rri_score");
const selectedHotspotKey = ref("");

const layerOptions = [
  { key: "rri_score", title: "综合风险", shortLabel: "RRI" },
  { key: "traffic_score", title: "交通暴露", shortLabel: "交通" },
  { key: "low_speed_score", title: "低速暴露", shortLabel: "低速" },
  { key: "environment_score", title: "环境暴露", shortLabel: "环境" },
];

const topVessels = computed(() => vessels.value.slice(0, 8));
const referenceSites = computed(() => regionalStats.value?.reference_sites || []);
const layerMeta = computed(() => layerOptions.find((item) => item.key === activeLayer.value) || layerOptions[0]);

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
    { label: "交通暴露", value: cell.traffic_score },
    { label: "低速暴露", value: cell.low_speed_score },
    { label: "环境暴露", value: cell.environment_score },
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

onMounted(async () => {
  try {
    await fetchDemoData();
    regionalStats.value = await fetchRegionalStats();
    overviewReport.value = await fetchOverviewReportPreview();
    if (sortedCells.value.length) {
      selectedHotspotKey.value = `${sortedCells.value[0].grid_lat}-${sortedCells.value[0].grid_lon}`;
    }
  } catch {
    // Shared loading and error state already handles rendering.
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
          平台基于 AIS 航迹与海洋环境数据，对研究区内区域热点、重点船舶与维护优先级进行统一展示。
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
            当前重点船舶
            <HintTooltip text="指当前样本中综合风险排序最高的船舶对象。" />
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
        <p>代表需要持续跟踪的区域暴露带。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">优先评估清洗</span>
        <strong class="stat-value">{{ summary.recommendation_counts["Prioritize cleaning assessment"] || 0 }}</strong>
        <p>建议优先纳入维护评估的船舶数量。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">低即时关注</span>
        <strong class="stat-value">{{ summary.recommendation_counts["Low immediate concern"] || 0 }}</strong>
        <p>当前暴露压力较低的船舶数量。</p>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Spatial View</p>
        <h3>
          区域主地图
          <HintTooltip text="地图基于真实风险格网绘制，显示加密后的展示网格、热点区域与港口/锚地参考点。" />
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
              <span>按 {{ item.shortLabel }} 分值排序与着色</span>
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
                  {{ selectedHotspot.risk_level }}风险，{{ selectedHotspot.vessel_count }} 艘船经过，
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
                <HintTooltip text="列表与地图使用相同图层口径，切换图层后排序会同步更新。" />
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
                <span>{{ item.risk_level }}风险，{{ item.vessel_count }} 艘船经过</span>
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
