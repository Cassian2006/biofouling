<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import InfoDisclosure from "../components/InfoDisclosure.vue";
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
      description: "显示该船在当前研究时间窗内被实际捕获到的轨迹范围。",
    },
    {
      title: "轨迹点数与时长",
      value: `${selectedVessel.value.ping_count} 点 / ${selectedVessel.value.track_duration_hours} 小时`,
      description: "点数与时长越充分，说明当前判断建立在更完整的行为观测之上。",
    },
    {
      title: "低速暴露比例",
      value: `${selectedVessel.value.low_speed_ratio ?? "暂无"}`,
      description: "低速暴露是首版规则里最重要的行为信号之一。",
    },
    {
      title: "平均位置",
      value: `${selectedVessel.value.mean_latitude}, ${selectedVessel.value.mean_longitude}`,
      description: "用于说明该船在本时间窗内主要活动于哪片海域。",
    },
    {
      title: "平均海温暴露",
      value: selectedVessel.value.mean_sst ?? "暂无",
      description: "来自真实环境匹配结果，用于补充解释环境压力。",
    },
    {
      title: "平均叶绿素暴露",
      value: selectedVessel.value.mean_chlorophyll_a ?? "暂无",
      description: "用于补充解释生物活跃环境是否可能放大污损压力。",
    },
    {
      title: "平均盐度暴露",
      value: selectedVessel.value.mean_salinity ?? "暂无",
      description: "用于区分不同水体环境下的暴露差异。",
    },
    {
      title: "平均海流 U/V",
      value:
        selectedVessel.value.mean_current_u !== null && selectedVessel.value.mean_current_v !== null
          ? `${selectedVessel.value.mean_current_u} / ${selectedVessel.value.mean_current_v}`
          : "暂无",
      description: "用于补充解释该船所处海区的水动力环境。",
    },
  ];
});

const staticFacts = computed(() => {
  if (!staticProfile.value) return [];
  return [
    {
      title: "画像来源",
      value: staticProfile.value.profile_source,
      description: "用于说明当前画像是 AIS 派生结果，还是已融合外部静态资料。",
    },
    {
      title: "船名 / IMO",
      value: `${staticProfile.value.vessel_name || "暂无"} / ${staticProfile.value.imo || "暂无"}`,
      description: "后续接入完整外部静态资料后，这里会显示更完整的识别信息。",
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
      title: "设计 / 观测吃水",
      value:
        staticProfile.value.design_draught_m !== null || staticProfile.value.observed_draught_m !== null
          ? `${staticProfile.value.design_draught_m ?? "暂无"} / ${staticProfile.value.observed_draught_m ?? "暂无"}`
          : "暂无",
      description: "当前至少可从 AIS 中提取观测吃水，后续可补设计吃水。",
    },
    {
      title: "主要目的地 / 航行状态",
      value: `${staticProfile.value.dominant_destination || "暂无"} / ${staticProfile.value.dominant_nav_status || "暂无"}`,
      description: "这是 AIS 派生画像中的基础行为特征。",
    },
    {
      title: "最近港口 / 锚地",
      value: nearestReference.value
        ? `${nearestReference.value.name}（${nearestReference.value.site_type}）`
        : "暂无",
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
      description: "后续接入离港、进港或维护事件后，可在这里查看最近记录。",
    },
    {
      title: "最近事件位置",
      value: validationSummary.value.latest_port_name || "暂无",
      description: "用于把分析判断与真实港口或案例位置对齐。",
    },
    {
      title: "外部来源数",
      value: validationSummary.value.source_count,
      description: "帮助快速了解当前校验覆盖的来源广度。",
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
      description: "为保持可读性进行了抽样，但仍保留整体走向。",
    },
    {
      title: "低速点数",
      value: vesselTrack.value.low_speed_point_count,
      description: "低速点越多，越值得关注停留与暴露积累。",
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
      title: "记录最密集时段",
      value: topPointWindow?.window_start || "暂无",
      description: `该时段共记录 ${topPointWindow?.point_count ?? 0} 个轨迹点。`,
    },
    {
      title: "低速暴露最高时段",
      value: topLowSpeedWindow?.window_start || "暂无",
      description: `该时段低速比例为 ${topLowSpeedWindow?.low_speed_ratio ?? "暂无"}。`,
    },
    {
      title: "平均航速最高时段",
      value: topSpeedWindow?.window_start || "暂无",
      description: `该时段平均航速约为 ${topSpeedWindow?.mean_sog ?? "暂无"} 节。`,
    },
  ];
});

const recommendationExplanation = computed(() => {
  if (!selectedVessel.value) return "";
  const mapping = {
    "Prioritize cleaning assessment":
      "当前规则判断该船值得优先检查维护窗口，适合作为清洗与进一步排查的重点对象。",
    "Monitor exposure trend":
      "当前规则判断该船尚未进入最高优先级，但存在持续暴露积累，适合继续跟踪趋势变化。",
    "Low immediate concern":
      "当前规则判断该船在本时间窗内的即时暴露压力较低，可暂列为较低优先级对象。",
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
      throw new Error("当前没有可用的单船详情数据。");
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
        <p class="section-kicker">Vessel Detail</p>
        <h2>围绕单船轨迹、时间趋势、画像信息与建议结果，建立一页式判读视图。</h2>
        <p class="support-text">
          本页用于回答三个问题：这艘船在当前时间窗里如何活动、为什么被判为当前优先级、以及已有哪些辅助资料可供解释或校验。
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

    <InfoDisclosure
      title="页面说明"
      summary="本页说明已折叠。页面重点展示单船证据链，而不是堆叠解释文字。"
    >
      <p>
        单船页将行为证据、环境暴露、船舶画像与外部校验入口放在同一页，目的是减少在多个页面之间来回跳转。
      </p>
      <p>
        轨迹图与趋势图负责说明“这艘船做了什么”，船舶画像与校验摘要负责补充“它是什么样的船、已有何种外部信息”。
      </p>
      <p>
        1.0 阶段优先保障信息完整与判读清晰，后续再继续增强地图交互和报告导出能力。
      </p>
    </InfoDisclosure>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Track</p>
        <h3>轨迹概览</h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card track-card">
          <div class="module-head">
            <h4>真实轨迹折线</h4>
            <span class="status-pill" v-if="vesselTrack">已接入 API</span>
          </div>
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

        <InfoDisclosure
          title="轨迹判读说明"
          summary="深色折线表示整体走向，绿色点为起点，橙色点为终点，浅色点为抽样后的低速位置。"
        >
          <p>先看整体形状，判断是否存在明显停留、折返或局部聚集。</p>
          <p>再看低速点位置，当前规则将低速暴露视为重要信号，因此会重点标示低速区域。</p>
          <p>1.0 先保证真实轨迹接入与清晰表达，后续再继续升级为带底图和时间筛选的地图轨迹。</p>
        </InfoDisclosure>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Trend</p>
        <h3>时间趋势</h3>
      </div>
      <div class="split-grid detail-layout">
        <article class="page-card trend-card">
          <div class="module-head">
            <h4>{{ vesselTrend ? `${vesselTrend.interval_hours} 小时分窗趋势` : "时间趋势图" }}</h4>
            <span class="status-pill" v-if="vesselTrend">真实分窗</span>
          </div>
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

        <InfoDisclosure
          title="趋势判读说明"
          summary="柱体表示记录点数量，蓝线表示平均航速，橙线表示低速比例。"
        >
          <p>先看柱体高度，判断各时段记录是否充分。</p>
          <p>再看蓝线与橙线位置，识别哪些时段更慢、更可能出现停留或持续低速活动。</p>
          <p>这组趋势用于补充“某条船为何被判入当前优先级”，而不仅是展示一条静态轨迹。</p>
        </InfoDisclosure>
      </div>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Summaries</p>
        <h3>轨迹与趋势摘要</h3>
      </div>
      <div class="card-grid">
        <article v-for="item in trackSummary" :key="item.title" class="page-card module-card">
          <div class="module-head">
            <h4>{{ item.title }}</h4>
          </div>
          <p class="feature-highlight small">{{ item.value }}</p>
          <p>{{ item.description }}</p>
        </article>
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
        <p class="section-kicker">Recommendation</p>
        <h3>建议解释</h3>
      </div>
      <article class="page-card text-card">
        <p>{{ recommendationExplanation }}</p>
      </article>
    </section>

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Signals</p>
        <h3>单船关键字段</h3>
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

    <section class="content-section">
      <div class="section-head">
        <p class="section-kicker">Switch</p>
        <h3>切换到其他重点船舶</h3>
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
