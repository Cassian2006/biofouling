<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { useDemoData } from "../composables/useDemoData";

const { summary, vessels, riskCells, loading, error, fetchDemoData, fetchOverviewReportPreview } = useDemoData();

const overviewReport = ref(null);

const moduleCards = [
  {
    title: "单船诊断",
    status: "已接入真实数据",
    description: "可查看真实单船特征、维护建议、轨迹走势和时间趋势，不再只是示意结构。",
  },
  {
    title: "区域风险地图",
    status: "已接入真实数据",
    description: "可查看真实区域格网、风险等级分布、图层切换和热点海域解释。",
  },
  {
    title: "情景模拟",
    status: "预留结构",
    description: "后续用于比较不同维护决策对风险和能效的影响。",
  },
  {
    title: "报告与接口",
    status: "已接入 API",
    description: "前端已优先通过 FastAPI 读取真实结果，不再只依赖静态 JSON 文件。",
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
  } catch (errorObject) {
    // The page already renders the shared loading/error state.
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
        <p class="section-kicker">总览 Dashboard</p>
        <h2>先看全局，再决定优先关注哪条船、哪个区域、哪一种维护动作。</h2>
        <p class="support-text">
          当前总览页已经接入真实摘要、真实船舶榜单、真实区域格网榜单，以及后端 API 返回的报告预览。
          用户进入平台后，可以先看全局，再决定往单船页还是区域页下钻。
        </p>
        <div class="hero-actions">
          <RouterLink class="cta-link" :to="`/vessels/${summary.top_vessel.mmsi}`">查看最高风险船舶</RouterLink>
          <RouterLink class="cta-link secondary" to="/regional-risk">查看区域风险页</RouterLink>
        </div>
      </article>

      <article class="page-card summary-stack">
        <div class="summary-metric">
          <span>当前测试时间窗</span>
          <strong>{{ summary.window_label }}</strong>
        </div>
        <div class="summary-metric">
          <span>已汇总船舶</span>
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

    <section class="stats-grid">
      <article class="page-card stat-card">
        <span class="stat-label">高风险格网</span>
        <strong class="stat-value">{{ summary.high_risk_cells }}</strong>
        <p>代表当前时间窗下最值得优先关注的热点海域。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">中风险格网</span>
        <strong class="stat-value">{{ summary.medium_risk_cells }}</strong>
        <p>代表可能存在持续暴露积累，需要继续观察的区域。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">优先评估清洗</span>
        <strong class="stat-value">{{ summary.recommendation_counts['Prioritize cleaning assessment'] || 0 }}</strong>
        <p>规则系统当前建议优先检查维护窗口的船舶数量。</p>
      </article>
      <article class="page-card stat-card">
        <span class="stat-label">低即时关注</span>
        <strong class="stat-value">{{ summary.recommendation_counts['Low immediate concern'] || 0 }}</strong>
        <p>当前暴露水平较低，可作为低优先级对象。</p>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">平台模块</p>
        <h3>当前哪些内容已经接入真实结果，哪些仍是预留结构</h3>
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
        <p class="section-kicker">高风险船舶榜单</p>
        <h3>当前来自真实船舶特征表，可直接跳转详情</h3>
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
        <p class="section-kicker">高风险区域榜单</p>
        <h3>点击后可直接跳到区域页，并带上默认热点选中状态</h3>
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
            <span>{{ item.risk_level }} 风险，{{ item.vessel_count }} 艘船经过</span>
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
        <p class="section-kicker">报告预览</p>
        <h3>当前总览页已经能通过后端接口拿到首版报告概览</h3>
      </div>
      <article class="page-card text-card">
        <p v-for="line in overviewReport?.lines || []" :key="line">{{ line }}</p>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">证据图表</p>
        <h3>这两张图仍然来自当前这批真实结果</h3>
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
        <p class="section-kicker">当前推荐结构</p>
        <h3>三类建议，用来帮助用户理解规则输出</h3>
      </div>
      <article class="page-card list-card">
        <div v-for="[label, value] in recommendationPairs" :key="label" class="list-row">
          <div>
            <strong>{{ label }}</strong>
            <span>这是当前演示阶段最核心的三类维护建议。</span>
          </div>
          <div class="list-metric">{{ value }} 艘</div>
        </div>
      </article>
    </section>
  </template>
</template>
