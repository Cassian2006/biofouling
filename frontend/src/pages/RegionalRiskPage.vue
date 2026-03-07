<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import InfoDisclosure from "../components/InfoDisclosure.vue";
import { useDemoData } from "../composables/useDemoData";

const route = useRoute();
const router = useRouter();
const { summary, riskCells, loading, error, fetchDemoData, fetchRegionalStats } = useDemoData();

const regionalStats = ref(null);
const pageError = ref("");
const activeLayer = ref("rri_score");
const selectedHotspotKey = ref("");

const layerOptions = [
  {
    key: "rri_score",
    title: "综合风险层",
    shortLabel: "RRI",
    description: "综合交通、低速与环境三类信号后的总体风险，用于识别重点区域。",
  },
  {
    key: "traffic_score",
    title: "交通暴露层",
    shortLabel: "交通",
    description: "用于观察轨迹点最密集、通行压力最大的区域。",
  },
  {
    key: "low_speed_score",
    title: "低速暴露层",
    shortLabel: "低速",
    description: "用于识别低速、等待或停留行为更集中的区域。",
  },
  {
    key: "environment_score",
    title: "环境暴露层",
    shortLabel: "环境",
    description: "用于观察环境条件对污损积累更敏感的区域。",
  },
];

const layerMeta = computed(() => layerOptions.find((item) => item.key === activeLayer.value) || layerOptions[0]);
const referenceSites = computed(() => regionalStats.value?.reference_sites || []);

const sortedCells = computed(() => {
  return [...riskCells.value]
    .filter((cell) => cell[activeLayer.value] !== null && cell[activeLayer.value] !== undefined)
    .sort((left, right) => (right[activeLayer.value] || 0) - (left[activeLayer.value] || 0));
});

const topCells = computed(() => sortedCells.value.slice(0, 10));

const selectedHotspot = computed(() => {
  if (!topCells.value.length) return null;
  const fallback = topCells.value[0];
  if (!selectedHotspotKey.value) return fallback;
  return topCells.value.find((item) => `${item.grid_lat}-${item.grid_lon}` === selectedHotspotKey.value) || fallback;
});

const layerSummaryCards = computed(() => {
  if (!regionalStats.value) return [];
  const values = sortedCells.value.map((item) => item[activeLayer.value] || 0);
  const averageValue = values.length ? Number((values.reduce((sum, item) => sum + item, 0) / values.length).toFixed(3)) : null;
  const activeCells = values.filter((value) => value >= 0.5).length;

  return [
    {
      title: "当前图层",
      value: layerMeta.value.title,
      description: layerMeta.value.description,
    },
    {
      title: "图层平均值",
      value: averageValue ?? "暂无",
      description: "表示研究区在该图层上的总体压力水平。",
    },
    {
      title: "高值格网数量",
      value: activeCells,
      description: "当前以 0.5 作为展示阈值，用于识别明显偏高区域。",
    },
    {
      title: "当前热点格网",
      value: selectedHotspot.value ? `${selectedHotspot.value.grid_lat}, ${selectedHotspot.value.grid_lon}` : "暂无",
      description: "表示当前图层下最值得优先解释的格网。",
    },
  ];
});

const hotspotFactors = computed(() => {
  const cell = selectedHotspot.value;
  if (!cell) return [];
  return [
    {
      title: "交通暴露分值",
      value: cell.traffic_score,
      description: "表示该格网内轨迹点密度对风险的贡献。",
    },
    {
      title: "低速暴露分值",
      value: cell.low_speed_score,
      description: "表示该格网内低速与停留行为的累积程度。",
    },
    {
      title: "环境暴露分值",
      value: cell.environment_score,
      description: "表示环境条件对污损压力的促进程度。",
    },
    {
      title: "最近参考点",
      value: cell.nearest_reference_name || "暂无",
      description: cell.nearest_reference_name
        ? `距离约 ${cell.nearest_reference_distance_km ?? "暂无"} km，类型为 ${cell.nearest_reference_type || "未知"}。`
        : "当前没有匹配到港口或锚地参考点。",
    },
  ];
});

const hotspotExplanation = computed(() => {
  const cell = selectedHotspot.value;
  if (!cell) return [];

  const factors = [
    { title: "交通暴露", value: cell.traffic_score || 0 },
    { title: "低速暴露", value: cell.low_speed_score || 0 },
    { title: "环境暴露", value: cell.environment_score || 0 },
  ].sort((left, right) => right.value - left.value);

  return [
    `当前图层为“${layerMeta.value.title}”，热点榜单按照该图层的分值排序。`,
    `该热点格网的综合风险值为 ${cell.rri_score}，共有 ${cell.vessel_count} 艘船经过，累计 ${cell.traffic_points} 个轨迹点。`,
    `从分值构成看，当前最主要的驱动因素是 ${factors[0].title}，其次是 ${factors[1].title}。`,
    cell.nearest_reference_name
      ? `从空间语义看，该热点更接近 ${cell.nearest_reference_name}，距离约 ${cell.nearest_reference_distance_km} km。`
      : "当前没有近港或锚地参考匹配，因此本轮解释以格网行为与环境信号为主。",
  ];
});

const svgGrid = computed(() => {
  if (!sortedCells.value.length) return null;
  const cells = sortedCells.value;
  const width = 920;
  const height = 420;
  const padding = 24;

  const lats = [...new Set(cells.map((item) => item.grid_lat))].sort((left, right) => left - right);
  const lons = [...new Set(cells.map((item) => item.grid_lon))].sort((left, right) => left - right);
  const minValue = Math.min(...cells.map((item) => item[activeLayer.value] || 0));
  const maxValue = Math.max(...cells.map((item) => item[activeLayer.value] || 0));
  const valueRange = Math.max(maxValue - minValue, 0.0001);
  const cellWidth = (width - padding * 2) / Math.max(lons.length, 1);
  const cellHeight = (height - padding * 2) / Math.max(lats.length, 1);

  const toColor = (value) => {
    const normalized = ((value || 0) - minValue) / valueRange;
    const hue = 190 - normalized * 155;
    const lightness = 90 - normalized * 42;
    return `hsl(${hue}, 72%, ${lightness}%)`;
  };

  const rects = cells.map((item) => {
    const lonIndex = lons.indexOf(item.grid_lon);
    const latIndex = lats.indexOf(item.grid_lat);
    const key = `${item.grid_lat}-${item.grid_lon}`;
    return {
      key,
      x: padding + lonIndex * cellWidth,
      y: padding + (lats.length - latIndex - 1) * cellHeight,
      width: Math.max(cellWidth - 2, 8),
      height: Math.max(cellHeight - 2, 8),
      fill: toColor(item[activeLayer.value]),
      active: selectedHotspotKey.value === key,
    };
  });

  return { width, height, rects };
});

function normalizeLayer(rawLayer) {
  return layerOptions.some((item) => item.key === rawLayer) ? rawLayer : "rri_score";
}

function applyRouteQuery() {
  activeLayer.value = normalizeLayer(typeof route.query.layer === "string" ? route.query.layer : "");
  const hotspotKey = typeof route.query.hotspot === "string" ? route.query.hotspot : "";
  selectedHotspotKey.value = hotspotKey;
}

function syncRouteQuery() {
  router.replace({
    query: {
      layer: activeLayer.value,
      hotspot: selectedHotspotKey.value || undefined,
    },
  });
}

function selectLayer(key) {
  activeLayer.value = key;
  selectedHotspotKey.value = "";
}

function selectHotspot(cell) {
  selectedHotspotKey.value = `${cell.grid_lat}-${cell.grid_lon}`;
}

function selectHotspotByKey(key) {
  selectedHotspotKey.value = key;
}

onMounted(async () => {
  pageError.value = "";
  try {
    await fetchDemoData();
    regionalStats.value = await fetchRegionalStats();
    applyRouteQuery();
  } catch (errorObject) {
    pageError.value = errorObject instanceof Error ? errorObject.message : "区域统计加载失败";
  }
});

watch(
  () => [route.query.layer, route.query.hotspot],
  () => {
    applyRouteQuery();
  },
);

watch([activeLayer, selectedHotspotKey], () => {
  syncRouteQuery();
});
</script>

<template>
  <section v-if="(loading && !regionalStats) || (!regionalStats && !pageError && !error)" class="page-card empty-state">
    正在加载区域风险页面...
  </section>

  <section v-else-if="pageError || (error && !regionalStats)" class="page-card empty-state error-state">
    {{ pageError || error }}
  </section>

  <template v-else-if="summary && regionalStats">
    <section class="hero-grid">
      <article class="page-card hero-copy-card">
        <p class="section-kicker">Regional Risk</p>
        <h2>区域风险空间分布与热点解释</h2>
        <p class="support-text">
          页面用于展示研究区格网分布、热点成因及其与港口、锚地参考点之间的空间关系。
        </p>
      </article>

      <article class="page-card summary-stack">
        <div class="summary-metric">
          <span>区域格网单元</span>
          <strong>{{ regionalStats.total_cells }}</strong>
        </div>
        <div class="summary-metric">
          <span>高风险格网</span>
          <strong>{{ regionalStats.risk_level_counts.high }}</strong>
        </div>
        <div class="summary-metric">
          <span>中风险格网</span>
          <strong>{{ regionalStats.risk_level_counts.medium }}</strong>
        </div>
        <div class="summary-metric">
          <span>平均 RRI</span>
          <strong>{{ regionalStats.average_rri }}</strong>
        </div>
      </article>
    </section>

    <InfoDisclosure
      title="页面说明"
      summary="区域页以图层比较与热点解释为主，说明内容已折叠收纳。"
    >
      <p>
        本页不仅用于展示高风险区域，更用于解释热点形成的主要驱动因素，并补充港口与锚地参考语义。
      </p>
      <p>
        图层切换用于区分综合风险、交通暴露、低速暴露与环境暴露，榜单和解释会随当前图层变化。
      </p>
    </InfoDisclosure>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Layers</p>
        <h3>图层切换</h3>
      </div>
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
          <span>{{ item.description }}</span>
        </button>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Matrix</p>
        <h3>格网矩阵预览</h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card regional-grid-card">
          <div class="module-head">
            <h4>{{ layerMeta.title }}</h4>
            <span class="status-pill">真实格网</span>
          </div>
          <div v-if="svgGrid" class="regional-grid-stage">
            <svg :viewBox="`0 0 ${svgGrid.width} ${svgGrid.height}`" class="regional-grid-svg" role="img" aria-label="区域图层矩阵图">
              <rect x="0" y="0" :width="svgGrid.width" :height="svgGrid.height" rx="18" class="trend-bg" />
              <rect
                v-for="cell in svgGrid.rects"
                :key="cell.key"
                :x="cell.x"
                :y="cell.y"
                :width="cell.width"
                :height="cell.height"
                rx="6"
                :fill="cell.fill"
                :class="{ 'grid-cell-active': cell.active }"
                @click="selectHotspotByKey(cell.key)"
              />
            </svg>
          </div>
        </article>

        <InfoDisclosure
          title="图层说明"
          summary="矩阵图用于稳定比较各图层下的高值区域，不替代地图视图。"
        >
          <p>{{ layerMeta.description }}</p>
          <p>矩阵图将地图中的格网结构抽离出来，适合比较不同图层下的高值区域变化。</p>
          <p>地图则负责回到真实海域语境，两者在表达上分工不同。</p>
        </InfoDisclosure>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Summary</p>
        <h3>当前图层摘要</h3>
      </div>
      <div class="card-grid">
        <article v-for="item in layerSummaryCards" :key="item.title" class="page-card module-card">
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
        <p class="section-kicker">Hotspot</p>
        <h3>热点解释</h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card text-card">
          <p v-for="line in hotspotExplanation" :key="line">{{ line }}</p>
        </article>
        <article class="page-card list-card">
          <div class="module-head">
            <h4>当前热点格网</h4>
          </div>
          <div class="list-row">
            <div>
              <strong>{{ selectedHotspot?.grid_lat }}, {{ selectedHotspot?.grid_lon }}</strong>
              <span>{{ selectedHotspot?.risk_level }}风险，{{ selectedHotspot?.vessel_count }} 艘船经过</span>
            </div>
            <div class="list-metric">
              <div>{{ layerMeta.shortLabel }} {{ selectedHotspot?.[activeLayer] }}</div>
              <div>RRI {{ selectedHotspot?.rri_score }}</div>
            </div>
          </div>
        </article>
      </div>
      <div class="card-grid">
        <article v-for="item in hotspotFactors" :key="item.title" class="page-card module-card">
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
        <p class="section-kicker">Ranking</p>
        <h3>热点格网榜单</h3>
      </div>
      <article class="page-card list-card">
        <button
          v-for="item in topCells"
          :key="`${item.grid_lat}-${item.grid_lon}`"
          type="button"
          class="list-row list-button"
          :class="{ active: `${item.grid_lat}-${item.grid_lon}` === `${selectedHotspot?.grid_lat}-${selectedHotspot?.grid_lon}` }"
          @click="selectHotspot(item)"
        >
          <div>
            <strong>{{ item.grid_lat }}, {{ item.grid_lon }}</strong>
            <span>
              {{ item.risk_level }}风险，{{ item.vessel_count }} 艘船经过，最近参考点为 {{ item.nearest_reference_name || "暂无" }}
            </span>
          </div>
          <div class="list-metric">
            <div>{{ layerMeta.shortLabel }} {{ item[activeLayer] }}</div>
            <div>{{ item.traffic_points }} 点</div>
          </div>
        </button>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Reference</p>
        <h3>参考点名录</h3>
      </div>
      <div class="card-grid">
        <article v-for="site in referenceSites" :key="site.site_id" class="page-card module-card">
          <div class="module-head">
            <h4>{{ site.name }}</h4>
            <span class="status-pill">{{ site.site_type }}</span>
          </div>
          <p class="feature-highlight small">{{ site.zone }}</p>
          <p>{{ site.description }}</p>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Map</p>
        <h3>区域地图</h3>
      </div>
      <InfoDisclosure
        title="地图说明"
        summary="地图用于回到真实海域语境，矩阵图用于稳定比较图层结果。"
      >
        <p>
          地图保留为空间位置参考视图，用于将格网热点与真实海域位置对应起来。矩阵图与地图互为补充，而不是相互替代。
        </p>
      </InfoDisclosure>
      <article class="page-card map-card">
        <iframe src="/demo/regional_demo_map.html" title="区域风险地图"></iframe>
      </article>
    </section>
  </template>
</template>
