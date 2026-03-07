<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import InfoDisclosure from "../components/InfoDisclosure.vue";
import { useDemoData } from "../composables/useDemoData";

const { summary, vessels, riskCells, loading, error, fetchDemoData, fetchOverviewReportPreview } = useDemoData();

const overviewReport = ref(null);

const moduleCards = [
  {
    title: "单船诊断",
    status: "已接入真实结果",
    description: "展示单船风险评分、轨迹、趋势、船舶画像与维护建议。",
  },
  {
    title: "区域风险识别",
    status: "已接入真实结果",
    description: "展示研究区格网风险、热点解释、参考点匹配与图层切换。",
  },
  {
    title: "报告预览",
    status: "已接入 API",
    description: "总览页与单船页均可读取后端生成的报告片段，用于演示结果交付方式。",
  },
  {
    title: "情景模拟",
    status: "预留结构",
    description: "1.0 先保留入口，后续用于比较不同维护策略下的风险变化。",
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
        <h2>先确认全局风险，再决定优先查看哪艘船、哪个热点区域。</h2>
        <p class="support-text">
          本页作为平台总入口，集中呈现当前时间窗的总体风险水平、重点对象与报告摘要，帮助用户快速建立判断顺序。
        </p>
        <div class="hero-actions">
          <RouterLink class="cta-link" :to="`/vessels/${summary.top_vessel.mmsi}`">查看最高风险船舶</RouterLink>
          <RouterLink class="cta-link secondary" to="/regional-risk">查看区域风险页</RouterLink>
        </div>
      </article>

      <article class="page-card summary-stack">
        <div class="summary-metric">
          <span>当前分析时间窗</span>
          <strong>{{ summary.window_label }}</strong>
        </div>
        <div class="summary-metric">
          <span>纳入分析的船舶</span>
          <strong>{{ summary.vessels_summarized }}</strong>
        </div>
        <div class="summary-metric">
          <span>区域格网单元</span>
          <strong>{{ summary.grid_cells }}</strong>
        </div>
        <div class="summary-metric">
          <span>当前最高风险船舶</span>
          <strong>{{ summary.top_vessel.mmsi }}</strong>
        </div>
      </article>
    </section>

    <InfoDisclosure
      title="页面说明"
      summary="说明文字已折叠收纳。本页重点用于回答“当前整体态势如何、优先关注对象是谁”。"
    >
      <p>
        总览页汇总展示三类信息：总体风险统计、重点船舶与重点区域清单、后端报告预览。用户通常先从这里建立全局判断，再进入单船页或区域页做深入分析。
      </p>
      <p>
        当前页面已接入真实 AIS 与环境处理结果，因此榜单、统计值和报告片段都来自真实样本，而不是静态占位文案。
      </p>
      <p>
        1.0 阶段的目标是形成完整、清晰、可解释的分析展示入口，而不是把所有运维功能都堆到界面上。
      </p>
    </InfoDisclosure>

    <section class="stats-grid">
      <article class="page-card stat-card">
        <span class="stat-label">高风险格网</span>
        <strong class="stat-value">{{ summary.high_risk_cells }}</strong>
        <p>代表当前时间窗内最值得优先关注的区域热点。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">中风险格网</span>
        <strong class="stat-value">{{ summary.medium_risk_cells }}</strong>
        <p>代表存在持续暴露积累、需要继续跟踪的区域。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">优先评估清洗</span>
        <strong class="stat-value">{{ summary.recommendation_counts["Prioritize cleaning assessment"] || 0 }}</strong>
        <p>系统建议优先检查维护窗口的船舶数量。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">低即时关注</span>
        <strong class="stat-value">{{ summary.recommendation_counts["Low immediate concern"] || 0 }}</strong>
        <p>当前暴露水平较低，可暂列为低优先级对象。</p>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Modules</p>
        <h3>当前版本已具备的展示模块</h3>
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
        <h3>高风险船舶清单</h3>
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
        <h3>高风险区域清单</h3>
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
        summary="三类建议用于帮助用户快速理解当前批次对象的维护优先级。"
      >
        <p>
          “优先评估清洗”表示该船在当前时间窗下呈现较高的综合暴露水平，适合作为维护窗口排查对象。
        </p>
        <p>
          “持续监测趋势”表示当前尚未达到最高优先级，但存在持续暴露积累，需要继续观察轨迹与环境变化。
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
        <h3>后端报告预览</h3>
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
