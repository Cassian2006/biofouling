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
    title: "定位",
    items: [
      "当前平台输出的是可解释的风险代理指标，不直接声称等于真实船底污损厚度。",
      "FPI 用于单船污损倾向判断，ECP 用于潜在代价惩罚表达，RRI 用于区域热点识别。",
      "冻结的竞赛主版本仍保持 15 天标准样本稳定，科学化评分升级作为当前第一优先级改进路径推进。",
    ],
  },
  {
    title: "科学升级结构",
    items: [
      "环境层不再按多个变量各自单调加分，而改成生理适宜层、生产力压力层、附着水动力层，再由行为暴露做最终修正。",
      "生理适宜层只看海温和盐度，生产力压力层只看叶绿素，附着水动力层只看合成后的 current_speed。",
      "行为暴露仍是主因，环境因子只做增强或削弱修正，避免短停高速对象因暖水环境被误判为超高风险。",
    ],
  },
  {
    title: "环境机制分量",
    items: [
      "T = sst_suitability：采用暖水促进、极端高温软回落的分段函数。",
      "S = salinity_suitability：采用低盐强惩罚、正常海水宽平台的闸门型结构。",
      "P = productivity_pressure_from_chl：将叶绿素作为生产力和传播压力代理，上升后封顶。",
      "H = hydrodynamic_attachment_score：先将 current_u 和 current_v 合成为 current_speed，再按低流速更利于附着、高流速更不利于附着的方向打分。",
    ],
  },
  {
    title: "FPI / ECP / RRI",
    items: [
      "EnvModifier = 0.40T + 0.20S + 0.25P + 0.15H。",
      "FPI = BehaviorExposure × (0.7 + 0.3 × EnvModifier)。",
      "ECP 仍是工程代理惩罚量，目前由 FPI、维护间隔、生产力压力、温度压力和低速暴露共同放大。",
      "RRI = 0.40 × EnvModifier + 0.25 × 交通疏密 + 0.20 × 锚地压力 + 0.15 × 行为暴露。",
    ],
  },
  {
    title: "参数来源",
    items: [
      "温度、盐度、叶绿素和流动条件的作用方向由机制与文献支持，但具体切点并非直接照抄某篇论文，而是按热带港区场景和研究区局地分布落地。",
      "current_speed 的切点使用冻结 15 天样本的局地百分位，而不是直接套实验室流速阈值。",
      "当前参数来源表、评分结构说明和科学性 review 已单独整理成文档，用于答辩与评审说明。",
    ],
  },
  {
    title: "科学边界",
    items: [
      "FPI、ECP、RRI 当前更适合做相对排序和优先级判断，不适合被解释成绝对生态真值。",
      "异常检测识别的是偏离常规暴露模式的对象，不直接等于“已发生真实严重污损”。",
      "LSTM 预测的是下一时间窗的 FPI proxy，属于短期趋势预警，不是长期生态演化模型。",
    ],
  },
  {
    title: "深度模块",
    items: [
      "时序预测模块使用单层 LSTM，将最近 8 个 6 小时窗口的行为与环境序列映射到下一窗口风险。",
      "异常检测模块使用全连接 Autoencoder，先学习常规暴露模式，再用重建误差识别偏离对象。",
      "这两个模块都增强平台的筛查和预警能力，但不替代规则链路。",
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
          本页用于说明当前平台的评分结构、科学边界与深度模块定位。重点不是把平台包装成黑箱，而是明确哪些环节有机制支撑、哪些环节属于工程先验，以及当前结果更适合如何解释。
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
