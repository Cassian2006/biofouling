<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
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
    description: "把交通、低速和环境三个维度综合后的总风险，用来判断哪里最值得优先关注。",
  },
  {
    key: "traffic_score",
    title: "交通暴露层",
    shortLabel: "交通",
    description: "看哪里通过的轨迹点最多、交通压力最大，更适合解释拥挤和频繁经过的区域。",
  },
  {
    key: "low_speed_score",
    title: "低速暴露层",
    shortLabel: "低速",
    description: "看哪里低速与停留行为更集中，更适合解释等待、慢速机动和暴露积累。",
  },
  {
    key: "environment_score",
    title: "环境暴露层",
    shortLabel: "环境",
    description: "看哪里环境条件对污损更友好，更适合解释为什么某些区域天然更敏感。",
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
      description: "表示整个研究区在当前图层上的平均压力水平。",
    },
    {
      title: "高值格网数量",
      value: activeCells,
      description: "当前用 0.5 作为展示阈值，帮助快速识别明显偏高的区域。",
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
      description: "表示该格网内轨迹点密度对区域风险的贡献。",
    },
    {
      title: "低速暴露分值",
      value: cell.low_speed_score,
      description: "表示该格网内低速、停留或缓行行为的累积程度。",
    },
    {
      title: "环境暴露分值",
      value: cell.environment_score,
      description: "表示该格网在环境条件上对污损积累的潜在促进作用。",
    },
    {
      title: "最近参考点",
      value: cell.nearest_reference_name || "暂无",
      description: cell.nearest_reference_name
        ? `当前距离约 ${cell.nearest_reference_distance_km ?? "暂无"} km，类型为 ${cell.nearest_reference_type || "未知"}。`
        : "当前还没有匹配到港口或锚地参考点。",
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
    `当前图层关注的是“${layerMeta.value.title}”，所以榜单和颜色优先按 ${layerMeta.value.shortLabel} 排序。`,
    `这个热点格网的综合风险值为 ${cell.rri_score}，共有 ${cell.vessel_count} 艘船经过，累计 ${cell.traffic_points} 个轨迹点。`,
    `如果拆成三个构成项，当前最强的驱动因素是 ${factors[0].title}，其次是 ${factors[1].title}。`,
    cell.nearest_reference_name
      ? `从地理语义上看，它离 ${cell.nearest_reference_name} 更近，距离约 ${cell.nearest_reference_distance_km} km，可作为近港或锚地解释的参考。`
      : "当前还没有近港或锚地参考匹配，因此这一轮解释仍以格网行为与环境信号为主。",
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
    正在加载区域风险页...
  </section>

  <section v-else-if="pageError || (error && !regionalStats)" class="page-card empty-state error-state">
    {{ pageError || error }}
  </section>

  <template v-else-if="summary && regionalStats">
    <section class="hero-grid">
      <article class="page-card hero-copy-card">
        <p class="section-kicker">区域风险页</p>
        <h2>这一页现在不仅能切换风险图层，还能告诉你热点更靠近哪个港口或锚地。</h2>
        <p class="support-text">
          区域页要回答三个问题：哪里最值得关注、热点主要由什么驱动、它更像是近港风险还是锚地风险。
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

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">图层切换</p>
        <h3>先决定你现在想看的是哪一种风险解释维度</h3>
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
        <p class="section-kicker">图层预览</p>
        <h3>先用格网矩阵看清当前图层在整个研究区里的分布</h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card regional-grid-card">
          <div class="module-head">
            <h4>{{ layerMeta.title }}</h4>
            <span class="status-pill">真实格网</span>
          </div>
          <p class="support-text">
            这张矩阵图不替代地图，它的作用是在切换图层时，更稳定地看见不同格网的高低变化。
          </p>
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

        <article class="page-card list-card">
          <div class="module-head">
            <h4>如何理解当前图层</h4>
          </div>
          <div class="list-row">
            <div>
              <strong>当前图层</strong>
              <span>{{ layerMeta.description }}</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>矩阵图的意义</strong>
              <span>它把地图中的格网结构抽出来，专门帮助你比较不同图层下的高值区域变化。</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>加入参考层之后</strong>
              <span>热点现在不只停留在经纬度层面，还能看到它离哪个港口或锚地更近。</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">当前图层摘要</p>
        <h3>把当前维度下最关键的四个量先提出来</h3>
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
        <p class="section-kicker">热点解释</p>
        <h3>先拆开看当前热点格网为什么会排到前面</h3>
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
              <span>
                {{ selectedHotspot?.risk_level }} 风险，{{ selectedHotspot?.vessel_count }} 艘船经过
              </span>
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
        <p class="section-kicker">热点格网榜单</p>
        <h3>这里按当前选中的图层重新排序，不再只看综合风险</h3>
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
              {{ item.risk_level }} 风险，{{ item.vessel_count }} 艘船经过，
              最近参考点为 {{ item.nearest_reference_name || "暂无" }}
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
        <p class="section-kicker">参考层名录</p>
        <h3>当前先用轻量港口与锚地点位帮助解释地理语义</h3>
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
        <p class="section-kicker">地图参考</p>
        <h3>地图仍然保留，帮助对照真实地理位置</h3>
      </div>
      <article class="page-card text-card">
        <p>
          这里保留原始区域地图，是为了帮助把格网热点和真实海域位置对应起来。矩阵图负责比较图层，地图负责回到地理语境，两者并不冲突。
        </p>
      </article>
      <article class="page-card map-card">
        <iframe src="/demo/regional_demo_map.html" title="区域风险地图"></iframe>
      </article>
    </section>
  </template>
</template>
