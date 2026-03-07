<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { useDemoData } from "../composables/useDemoData";

const route = useRoute();
const {
  summary,
  loading,
  error,
  fetchDemoData,
  fetchVesselDetail,
  fetchVesselReportPreview,
  fetchVesselTrack,
  fetchVesselTrend,
} = useDemoData();

const vesselDetail = ref(null);
const vesselTrack = ref(null);
const vesselTrend = ref(null);
const reportPreview = ref(null);
const pageError = ref("");
const trackError = ref("");
const trendError = ref("");

const selectedVessel = computed(() => vesselDetail.value?.vessel || null);
const peerVessels = computed(() => vesselDetail.value?.peer_vessels || []);
const staticProfile = computed(() => vesselDetail.value?.static_profile || null);
const validationSummary = computed(() => vesselDetail.value?.validation_summary || null);
const nearestReference = computed(() => vesselDetail.value?.nearest_reference || null);

const vesselFacts = computed(() => {
  if (!selectedVessel.value) return [];
  return [
    {
      title: "轨迹时间窗",
      value: `${selectedVessel.value.track_start} -> ${selectedVessel.value.track_end}`,
      description: "表示这艘船在当前研究时间窗内实际被捕获到的轨迹范围。",
    },
    {
      title: "轨迹点数与时长",
      value: `${selectedVessel.value.ping_count} 点 / ${selectedVessel.value.track_duration_hours} 小时`,
      description: "点数越多、时长越长，说明当前判断建立在更充分的行为观察之上。",
    },
    {
      title: "低速暴露比例",
      value: `${selectedVessel.value.low_speed_ratio ?? "暂无"}`,
      description: "低速比例是当前规则里最重要的行为暴露信号之一。",
    },
    {
      title: "平均位置",
      value: `${selectedVessel.value.mean_latitude}, ${selectedVessel.value.mean_longitude}`,
      description: "用于说明这艘船在当前时间窗内大致活动在哪一片海域。",
    },
    {
      title: "平均海温暴露",
      value: selectedVessel.value.mean_sst ?? "暂无",
      description: "当前已接入真实环境暴露结果，不再只看 AIS 行为本身。",
    },
    {
      title: "平均叶绿素暴露",
      value: selectedVessel.value.mean_chlorophyll_a ?? "暂无",
      description: "用于补充解释生物活跃环境是否可能放大污损压力。",
    },
    {
      title: "平均盐度暴露",
      value: selectedVessel.value.mean_salinity ?? "暂无",
      description: "盐度进入后，可以开始区分不同水体环境下的暴露差异。",
    },
    {
      title: "平均海流 U/V",
      value:
        selectedVessel.value.mean_current_u !== null && selectedVessel.value.mean_current_v !== null
          ? `${selectedVessel.value.mean_current_u} / ${selectedVessel.value.mean_current_v}`
          : "暂无",
      description: "用于补充解释船舶所处海区的水动力环境。",
    },
  ];
});

const staticFacts = computed(() => {
  if (!staticProfile.value) return [];
  return [
    {
      title: "画像来源",
      value: staticProfile.value.profile_source,
      description: "当前画像是仅由 AIS 派生，还是已经融合了外部静态资料。",
    },
    {
      title: "船名 / IMO",
      value: `${staticProfile.value.vessel_name || "暂无"} / ${staticProfile.value.imo || "暂无"}`,
      description: "后续补入外部静态表后，这里会显示更完整的识别信息。",
    },
    {
      title: "船型 / 船旗",
      value: `${staticProfile.value.ship_type || "暂无"} / ${staticProfile.value.flag || "暂无"}`,
      description: "这是后续做船型分层和辅助解释的重要基础。",
    },
    {
      title: "长度 / 型宽",
      value:
        staticProfile.value.length_m !== null && staticProfile.value.beam_m !== null
          ? `${staticProfile.value.length_m}m / ${staticProfile.value.beam_m}m`
          : "暂无",
      description: "如果后续拿到外部资料，这里会优先显示更准确的尺度信息。",
    },
    {
      title: "设计 / 观测吃水",
      value:
        staticProfile.value.design_draught_m !== null || staticProfile.value.observed_draught_m !== null
          ? `${staticProfile.value.design_draught_m ?? "暂无"} / ${staticProfile.value.observed_draught_m ?? "暂无"}`
          : "暂无",
      description: "当前至少可以从 AIS 中得到观测吃水，后续可用外部资料补设计吃水。",
    },
    {
      title: "主目的地 / 航行状态",
      value: `${staticProfile.value.dominant_destination || "暂无"} / ${staticProfile.value.dominant_nav_status || "暂无"}`,
      description: "这是当前由 AIS 派生出的基础船舶画像，用来补充行为解释。",
    },
    {
      title: "最近港口 / 锚地",
      value: nearestReference.value
        ? `${nearestReference.value.name} (${nearestReference.value.site_type})`
        : "暂无",
      description: nearestReference.value
        ? `当前按船舶平均位置匹配，距离约 ${vesselDetail.value?.nearest_reference_distance_km ?? "暂无"} km。`
        : "当前还没有可用的港口或锚地参考匹配。",
    },
  ];
});

const validationFacts = computed(() => {
  if (!validationSummary.value) return [];
  return [
    {
      title: "外部校验事件数",
      value: validationSummary.value.event_count,
      description: "表示当前是否已经有外部事件可以用来对照 AIS 与分析结果。",
    },
    {
      title: "最近校验事件",
      value: validationSummary.value.latest_event_type || "暂无",
      description: "如果后续接入到离港或港口事件，这里会显示最近一条外部记录。",
    },
    {
      title: "最近事件位置",
      value: validationSummary.value.latest_port_name || "暂无",
      description: "帮助把模型判断和真实港口或案例位置对应起来。",
    },
    {
      title: "外部来源数",
      value: validationSummary.value.source_count,
      description: "后续如果有多个来源，这里能快速看出当前校验覆盖情况。",
    },
  ];
});

const trackSummary = computed(() => {
  if (!vesselTrack.value) return [];
  return [
    {
      title: "原始轨迹点",
      value: vesselTrack.value.point_count,
      description: "后台保留的真实轨迹点数量。",
    },
    {
      title: "前端渲染点",
      value: vesselTrack.value.rendered_point_count,
      description: "为了页面可读性做了抽样，但仍保留整体走向。",
    },
    {
      title: "低速点数",
      value: vesselTrack.value.low_speed_point_count,
      description: "低速点越多，越值得关注停留与暴露累积。",
    },
  ];
});

const trendSummary = computed(() => {
  if (!vesselTrend.value?.windows?.length) return [];
  const windows = vesselTrend.value.windows;
  const topPointWindow = [...windows].sort((a, b) => b.point_count - a.point_count)[0];
  const topLowSpeedWindow = [...windows].sort((a, b) => (b.low_speed_ratio ?? 0) - (a.low_speed_ratio ?? 0))[0];
  const topSpeedWindow = [...windows].sort((a, b) => (b.mean_sog ?? 0) - (a.mean_sog ?? 0))[0];

  return [
    {
      title: "最密集时间段",
      value: topPointWindow?.window_start || "暂无",
      description: `该时间段捕获到 ${topPointWindow?.point_count ?? 0} 个点，代表当时轨迹记录最密。`,
    },
    {
      title: "低速暴露最高时段",
      value: topLowSpeedWindow?.window_start || "暂无",
      description: `该时间段低速比例为 ${topLowSpeedWindow?.low_speed_ratio ?? "暂无"}。`,
    },
    {
      title: "均速最高时段",
      value: topSpeedWindow?.window_start || "暂无",
      description: `该时间段均速约为 ${topSpeedWindow?.mean_sog ?? "暂无"} 节。`,
    },
  ];
});

const recommendationExplanation = computed(() => {
  if (!selectedVessel.value) return "";
  const mapping = {
    "Prioritize cleaning assessment":
      "当前规则判断这艘船值得优先检查维护窗口，后续最适合补充清洗时机与成本视角。",
    "Monitor exposure trend":
      "当前规则判断这艘船还没有进入最高优先级，但存在持续暴露趋势，适合继续观察。",
    "Low immediate concern":
      "当前规则判断这艘船在本时间窗内即时压力较低，可暂时放在较低优先级。",
  };
  return mapping[selectedVessel.value.recommendation] || "这是当前首版规则系统给出的建议结果。";
});

const svgTrack = computed(() => {
  if (!vesselTrack.value?.points?.length) return null;

  const width = 920;
  const height = 460;
  const padding = 36;
  const minLon = vesselTrack.value.min_longitude;
  const maxLon = vesselTrack.value.max_longitude;
  const minLat = vesselTrack.value.min_latitude;
  const maxLat = vesselTrack.value.max_latitude;
  const lonRange = Math.max(maxLon - minLon, 0.0001);
  const latRange = Math.max(maxLat - minLat, 0.0001);

  const project = (point) => {
    const x = padding + ((point.longitude - minLon) / lonRange) * (width - padding * 2);
    const y = height - padding - ((point.latitude - minLat) / latRange) * (height - padding * 2);
    return { ...point, x, y };
  };

  const projected = vesselTrack.value.points.map(project);
  const path = projected
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ");

  return {
    width,
    height,
    path,
    lowSpeedPoints: projected.filter((point) => point.is_low_speed).slice(0, 48),
    start: projected[0],
    end: projected[projected.length - 1],
  };
});

const svgTrend = computed(() => {
  if (!vesselTrend.value?.windows?.length) return null;

  const width = 920;
  const height = 340;
  const paddingX = 44;
  const topPadding = 28;
  const bottomPadding = 44;
  const innerWidth = width - paddingX * 2;
  const innerHeight = height - topPadding - bottomPadding;
  const windows = vesselTrend.value.windows;
  const maxSog = Math.max(vesselTrend.value.max_mean_sog || 0, 0.1);
  const maxLowSpeed = Math.max(vesselTrend.value.max_low_speed_ratio || 0, 0.1);

  const projectX = (index) => {
    if (windows.length === 1) return width / 2;
    return paddingX + (index / (windows.length - 1)) * innerWidth;
  };

  const projectSogY = (value) => topPadding + innerHeight - ((value || 0) / maxSog) * innerHeight;
  const projectLowSpeedY = (value) => topPadding + innerHeight - ((value || 0) / maxLowSpeed) * innerHeight;

  const speedPath = windows
    .map((item, index) => `${index === 0 ? "M" : "L"} ${projectX(index).toFixed(2)} ${projectSogY(item.mean_sog).toFixed(2)}`)
    .join(" ");

  const lowSpeedPath = windows
    .map(
      (item, index) => `${index === 0 ? "M" : "L"} ${projectX(index).toFixed(2)} ${projectLowSpeedY(item.low_speed_ratio).toFixed(2)}`,
    )
    .join(" ");

  const bars = windows.map((item, index) => {
    const x = projectX(index) - 12;
    const barHeight = (item.point_count / Math.max(vesselTrend.value.max_point_count, 1)) * innerHeight;
    return {
      label: item.window_start.slice(5, 16).replace("T", " "),
      pointCount: item.point_count,
      x,
      y: topPadding + innerHeight - barHeight,
      width: 24,
      height: barHeight,
      cx: projectX(index),
      sogY: projectSogY(item.mean_sog),
      lowSpeedY: projectLowSpeedY(item.low_speed_ratio),
    };
  });

  return {
    width,
    height,
    bars,
    speedPath,
    lowSpeedPath,
  };
});

async function loadPageData() {
  pageError.value = "";
  trackError.value = "";
  trendError.value = "";
  vesselTrack.value = null;
  vesselTrend.value = null;

  try {
    await fetchDemoData();
    const mmsi = route.params.mmsi ? String(route.params.mmsi) : summary.value?.top_vessel?.mmsi;
    if (!mmsi) {
      throw new Error("当前没有可用的船舶详情数据");
    }

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
    <section class="hero-grid">
      <article class="page-card hero-copy-card">
        <p class="section-kicker">单船详情页</p>
        <h2>这一页现在同时呈现真实轨迹、时间趋势、船舶画像和外部校验占位。</h2>
        <p class="support-text">
          这里要回答的不只是“这艘船去了哪里”，还包括“它是什么样的船”“当前有哪些外部资料已接入”“为什么系统把它放在当前优先级”。
        </p>
      </article>

      <article class="page-card summary-stack">
        <div class="summary-metric">
          <span>当前查看 MMSI</span>
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

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">轨迹示意</p>
        <h3>先看这艘船在研究时间窗内的大致移动走势</h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card track-card">
          <div class="module-head">
            <h4>真实轨迹折线</h4>
            <span class="status-pill" v-if="vesselTrack">已接入 API</span>
          </div>
          <p class="support-text">
            深色折线表示轨迹整体走向，绿色点是起点，橙色点是终点，浅色点表示抽样后的低速位置。
          </p>
          <div v-if="svgTrack" class="track-stage">
            <svg :viewBox="`0 0 ${svgTrack.width} ${svgTrack.height}`" class="track-svg" role="img" aria-label="单船轨迹图">
              <rect x="0" y="0" :width="svgTrack.width" :height="svgTrack.height" rx="18" class="track-bg" />
              <path :d="svgTrack.path" class="track-line" />
              <circle
                v-for="point in svgTrack.lowSpeedPoints"
                :key="`${point.timestamp}-${point.x}-${point.y}`"
                :cx="point.x"
                :cy="point.y"
                r="3.2"
                class="track-low-speed"
              />
              <circle :cx="svgTrack.start.x" :cy="svgTrack.start.y" r="6.5" class="track-start" />
              <circle :cx="svgTrack.end.x" :cy="svgTrack.end.y" r="6.5" class="track-end" />
            </svg>
          </div>
          <div v-else class="empty-state track-empty">
            {{ trackError || "当前没有可展示的轨迹数据。" }}
          </div>
        </article>

        <article class="page-card list-card">
          <div class="module-head">
            <h4>如何理解这张图</h4>
          </div>
          <div class="list-row">
            <div>
              <strong>先看形状</strong>
              <span>这一版先解决“真实轨迹是否已经接入”，帮助判断是否存在明显停留、折返和局部暴露。</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>再看低速点</strong>
              <span>当前规则把低速暴露视为重要信号，所以专门标出低速点，方便看停留位置。</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>后续会升级为地图轨迹</strong>
              <span>1.0 先把真实轨迹接进来，后续再加底图、时间筛选和港口锚地叠层。</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">时间趋势</p>
        <h3>再看它在每个时间段里是更慢还是更活跃</h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card trend-card">
          <div class="module-head">
            <h4>{{ vesselTrend ? `${vesselTrend.interval_hours} 小时趋势` : "时间趋势图" }}</h4>
            <span class="status-pill" v-if="vesselTrend">真实分窗</span>
          </div>
          <p class="support-text">
            柱形表示该时间段记录点数量，蓝线表示平均航速，橙线表示低速比例。三者叠在一起可以快速看出“何时更慢、何时更密集”。
          </p>
          <div v-if="svgTrend" class="trend-stage">
            <svg :viewBox="`0 0 ${svgTrend.width} ${svgTrend.height}`" class="trend-svg" role="img" aria-label="单船时间趋势图">
              <rect x="0" y="0" :width="svgTrend.width" :height="svgTrend.height" rx="18" class="trend-bg" />
              <rect
                v-for="bar in svgTrend.bars"
                :key="`bar-${bar.label}`"
                :x="bar.x"
                :y="bar.y"
                :width="bar.width"
                :height="bar.height"
                rx="6"
                class="trend-bar"
              />
              <path :d="svgTrend.speedPath" class="trend-speed-line" />
              <path :d="svgTrend.lowSpeedPath" class="trend-low-line" />
              <circle
                v-for="bar in svgTrend.bars"
                :key="`speed-${bar.label}`"
                :cx="bar.cx"
                :cy="bar.sogY"
                r="4"
                class="trend-speed-dot"
              />
              <circle
                v-for="bar in svgTrend.bars"
                :key="`slow-${bar.label}`"
                :cx="bar.cx"
                :cy="bar.lowSpeedY"
                r="4"
                class="trend-low-dot"
              />
            </svg>
            <div class="trend-labels">
              <span v-for="bar in svgTrend.bars" :key="bar.label">{{ bar.label }}</span>
            </div>
          </div>
          <div v-else class="empty-state track-empty">
            {{ trendError || "当前没有可展示的趋势数据。" }}
          </div>
        </article>

        <article class="page-card list-card">
          <div class="module-head">
            <h4>趋势图告诉我们什么</h4>
          </div>
          <div class="list-row">
            <div>
              <strong>柱子看记录密度</strong>
              <span>柱子越高，说明该时间段捕获到的轨迹点越多，通常意味着观察更充分。</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>蓝线看平均航速</strong>
              <span>均速越低，越可能对应停留、等待、慢速机动等更容易累积暴露的状态。</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>橙线看低速比例</strong>
              <span>当橙线持续处于高位时，说明这艘船在多个时间窗里都维持低速，更值得重点关注。</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">轨迹摘要</p>
        <h3>先把轨迹层里最重要的三个量提出来</h3>
      </div>
      <div class="card-grid">
        <article v-for="item in trackSummary" :key="item.title" class="page-card module-card">
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
        <p class="section-kicker">趋势摘要</p>
        <h3>把时间维度里最值得注意的三个片段提出来</h3>
      </div>
      <div class="card-grid">
        <article v-for="item in trendSummary" :key="item.title" class="page-card module-card">
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
        <p class="section-kicker">建议解释</p>
        <h3>先解释系统为什么把这艘船放在当前优先级</h3>
      </div>
      <article class="page-card text-card">
        <p>{{ recommendationExplanation }}</p>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">真实字段快照</p>
        <h3>这些内容已经直接来自单船详情接口</h3>
      </div>
      <div class="card-grid">
        <article v-for="item in vesselFacts" :key="item.title" class="page-card module-card">
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
        <p class="section-kicker">船舶画像</p>
        <h3>这一层开始补“它是什么样的船”，而不只看“它做了什么”</h3>
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
        <p class="section-kicker">外部校验摘要</p>
        <h3>这里预留给到离港、港口事件或其他外部案例核验</h3>
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
        <p class="section-kicker">报告预览</p>
        <h3>这里是后端返回的单船报告片段</h3>
      </div>
      <article class="page-card text-card">
        <p v-for="line in reportPreview?.lines || []" :key="line">{{ line }}</p>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">切换其他船舶</p>
        <h3>当前先用同批次中的其他高风险船舶做切换入口</h3>
      </div>
      <article class="page-card list-card">
        <RouterLink
          v-for="item in peerVessels"
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
            <div>{{ item.track_duration_hours }} 小时</div>
          </div>
        </RouterLink>
      </article>
    </section>
  </template>
</template>
