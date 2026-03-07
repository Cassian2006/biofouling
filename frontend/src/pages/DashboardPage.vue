<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import InfoDisclosure from "../components/InfoDisclosure.vue";
import { useDemoData } from "../composables/useDemoData";

const { summary, vessels, riskCells, loading, error, fetchDemoData, fetchOverviewReportPreview } = useDemoData();

const overviewReport = ref(null);

const moduleCards = [
  {
    title: "单船分析",
    status: "已接入真实结果",
    description: "展示单船风险评分、轨迹、时间趋势、船舶画像与维护建议。",
  },
  {
    title: "区域风险识别",
    status: "已接入真实结果",
    description: "展示研究区格网风险、热点解释、参考点匹配与图层切换。",
  },
  {
    title: "报告预览",
    status: "已接入 API",
    description: "总览页与单船页可直接读取后端生成的报告片段，用于展示结果交付形式。",
  },
  {
    title: "情景模拟",
    status: "预留结构",
    description: "1.0 阶段保留产品入口，后续用于比较不同维护策略下的风险变化。",
  },
];

const topVessels = computed(() => vessels.value.slice(0, 6));
const topRiskCells = computed(() => riskCells.value.slice(0, 6));

const recommendationPairs = computed(() => {
  if (!summary.value) return [];
  return [
    ["优先评估清洗", summary.value.recommendation_counts["Prioritize cleaning assessment"] || 0],
    ["持续监测趋势", summary.value.recommendation_counts["Monitor exposure trend"] || 0],
    ["低即时关注", summary.value.recommendation_counts["Low immediate concern"] || 0],
  ];
});

function hotspotQuery(item) {
  return {
    path: "/regional-risk",
    query: {
      layer: "rri_score",
      hotspot: `${item.grid_lat}-${item.grid_lon}`,
    },
  };
}

onMounted(async () => {
  try {
    await fetchDemoData();
    overviewReport.value = await fetchOverviewReportPreview();
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

  <template v-else-if="summary">
    <section class="hero-grid">
      <article class="page-card hero-copy-card">
        <p class="section-kicker">Overview</p>
        <h2>新加坡海峡船舶生物污损风险总览</h2>
        <p class="support-text">
          平台基于 AIS 航迹与海洋环境数据，对研究区内船舶暴露水平、区域热点分布与维护优先级进行集中展示。
        </p>
        <div class="hero-actions">
          <RouterLink class="cta-link" :to="`/vessels/${summary.top_vessel.mmsi}`">查看重点船舶</RouterLink>
          <RouterLink class="cta-link secondary" to="/regional-risk">查看区域风险页</RouterLink>
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
          <span>当前重点船舶</span>
          <strong>{{ summary.top_vessel.mmsi }}</strong>
        </div>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Map</p>
        <h3>区域主地图</h3>
      </div>
      <article class="page-card map-card map-card-compact">
        <iframe src="/demo/regional_demo_map.html" title="区域风险主地图"></iframe>
      </article>
      <InfoDisclosure
        title="地图说明"
        summary="首页优先展示真实区域地图，用于直接呈现研究区热点分布与空间范围。"
      >
        <p>
          该地图基于当前真实格网结果生成，展示研究区内风险热区与重点轨迹分布，是平台空间分析能力的主要入口。
        </p>
        <p>
          用户进入首页后，可先通过地图确认研究区范围、热点位置与轨迹分布，再进入单船页或区域页查看更细的解释信息。
        </p>
      </InfoDisclosure>
    </section>

    <section class="stats-grid">
      <article class="page-card stat-card">
        <span class="stat-label">高风险格网</span>
        <strong class="stat-value">{{ summary.high_risk_cells }}</strong>
        <p>代表当前时间窗内风险水平最高的区域热点。</p>
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

    <InfoDisclosure
      title="总览页说明"
      summary="总览页用于集中呈现区域空间结果、总体统计和重点对象列表。"
    >
      <p>
        当前页面已接入真实 AIS 与环境处理结果，因此地图、榜单、统计值和报告片段均来自真实样本，而不是静态占位内容。
      </p>
      <p>
        1.0 阶段的重点是形成清晰、正式、可解释的分析总入口，而不是在首页堆叠过多操作指引。
      </p>
    </InfoDisclosure>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Modules</p>
        <h3>已接入的主要模块</h3>
      </div>
      <div class="card-grid">
        <article v-for="item in moduleCards" :key="item.title" class="page-card module-card">
          <div class="module-head">
            <h4>{{ item.title }}</h4>
            <span class="status-pill">{{ item.status }}</span>
          </div>
          <p>{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Vessels</p>
        <h3>重点船舶列表</h3>
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
        <p class="section-kicker">Hotspots</p>
        <h3>重点区域列表</h3>
      </div>
      <article class="page-card list-card">
        <RouterLink
          v-for="item in topRiskCells"
          :key="`${item.grid_lat}-${item.grid_lon}`"
          class="list-row link-row"
          :to="hotspotQuery(item)"
        >
          <div>
            <strong>{{ item.grid_lat }}, {{ item.grid_lon }}</strong>
            <span>{{ item.risk_level }}风险，{{ item.vessel_count }} 艘船经过</span>
          </div>
          <div class="list-metric">
            <div>RRI {{ item.rri_score }}</div>
            <div>{{ item.traffic_points }} 点</div>
          </div>
        </RouterLink>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Guide</p>
        <h3>建议类别说明</h3>
      </div>
      <InfoDisclosure
        title="判读口径"
        summary="三类建议用于说明当前样本中不同对象的维护优先级。"
      >
        <p>
          “优先评估清洗”表示该船在当前时间窗下呈现较高的综合暴露水平，适合作为维护窗口排查对象。
        </p>
        <p>
          “持续监测趋势”表示对象尚未达到最高优先级，但已存在持续暴露积累，需要继续观察。
        </p>
        <p>
          “低即时关注”表示当前窗口内暴露压力较低，可作为低优先级对象暂缓处理。
        </p>
      </InfoDisclosure>
      <article class="page-card list-card">
        <div v-for="[label, value] in recommendationPairs" :key="label" class="list-row">
          <div>
            <strong>{{ label }}</strong>
            <span>用于辅助理解当前批次的维护建议分布。</span>
          </div>
          <div class="list-metric">{{ value }} 艘</div>
        </div>
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

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Evidence</p>
        <h3>辅助图表</h3>
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
  </template>
</template>
