<script setup>
defineProps({
  open: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["close"]);

const sections = [
  {
    title: "指标定位",
    items: [
      "当前版本采用规则化估计，不直接输出生物附着的物理实测值，而是输出可解释的风险代理指标。",
      "FPI 反映单船污损倾向，ECP 反映潜在排放惩罚，RRI 反映区域级综合风险。",
    ],
  },
  {
    title: "FPI 计算",
    items: [
      "FPI = 0.5 × 行为暴露 + 0.3 × 环境暴露 + 0.2 × 维护间隔。",
      "行为暴露 = 0.35 × 停留时长 + 0.30 × 锚泊时长 + 0.20 × 低速时长 + 0.15 × 港口访问次数。",
      "停留、锚泊、低速和港口访问都会先按固定阈值归一化，再裁剪到 0 到 1 之间。",
    ],
  },
  {
    title: "环境暴露与 ECP",
    items: [
      "环境暴露 = 0.55 × 海表温度暴露 + 0.45 × 叶绿素暴露。",
      "海温使用 24°C 到 32°C 区间做归一化；叶绿素以 1.5 为上限归一化。",
      "ECP 以 FPI 为基础，再按暖水、高叶绿素和长时间低速给予倍率修正。",
      "若平均海温 ≥ 28°C，ECP 增加 15%；叶绿素 ≥ 0.5 增加 10%；低速时长 ≥ 48 小时再增加 5%。",
    ],
  },
  {
    title: "RRI 计算",
    items: [
      "RRI = 0.40 × 环境暴露 + 0.25 × 交通密度 + 0.20 × 锚地暴露 + 0.15 × 行为暴露。",
      "RRI 主要用于空间热区识别，因此更强调环境、交通和锚地压力。",
    ],
  },
  {
    title: "建议判定",
    items: [
      "若 FPI ≥ 0.70 或 ECP ≥ 0.85，建议优先评估清洗。",
      "若 FPI ≥ 0.40 或 ECP ≥ 0.55，建议持续监测暴露趋势。",
      "其余对象归为当前即时关注度较低。",
    ],
  },
];
</script>

<template>
  <transition name="drawer-fade">
    <div v-if="open" class="method-drawer-shell" @click.self="emit('close')">
      <aside class="method-drawer" role="dialog" aria-modal="true" aria-label="核心算法说明">
        <div class="method-drawer__head">
          <div>
            <p class="section-kicker">Method</p>
            <h3>核心算法说明</h3>
          </div>
          <button type="button" class="method-drawer__close" @click="emit('close')">关闭</button>
        </div>

        <p class="method-drawer__intro">
          本页说明当前版本平台如何计算 FPI、ECP 与 RRI，以及系统如何基于这些指标生成风险建议。
        </p>

        <section v-for="section in sections" :key="section.title" class="method-drawer__section">
          <h4>{{ section.title }}</h4>
          <ul class="method-drawer__list">
            <li v-for="item in section.items" :key="item">{{ item }}</li>
          </ul>
        </section>
      </aside>
    </div>
  </transition>
</template>
