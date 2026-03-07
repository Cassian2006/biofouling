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
      "1.5 阶段在规则链路之外新增 LSTM 时序预测，用于补充“下一时间窗风险走向”，而不是替代当前规则结果。",
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
    title: "LSTM 数据构建",
    items: [
      "预测模块先将清洗后的 AIS 与环境匹配结果按 6 小时窗口聚合，形成窗口级行为与环境特征。",
      "每个窗口至少保留 ping_count、coverage_ratio、mean_sog、max_sog、low_speed_ratio、mean_sst、mean_chlorophyll_a、mean_salinity、mean_current_u、mean_current_v 与当前窗口 FPI proxy。",
      "训练样本使用最近 8 个连续窗口作为输入，预测下一 1 个窗口的 FPI proxy；只有时间连续的序列才会进入训练集。",
      "当前 15 天真实窗口上共生成 5495 条窗口记录和 1160 条监督式序列样本。",
    ],
  },
  {
    title: "LSTM 训练流程",
    items: [
      "模型采用轻量单层 LSTM，hidden size 为 32，按船舶划分训练集与验证集，避免同一船的连续样本同时落入两侧。",
      "训练目标是回归下一窗口的连续 FPI proxy，而不是直接做三分类，这样可以保留风险变化的连续性。",
      "当前主模型保留基线版 uniform / uniform 训练口径，因为类别平衡版虽然改变了标签分布表现，但整体误差和稳定性不如基线。",
      "当前验证结果约为 MAE 0.1629、RMSE 0.2111、R² 0.5254，说明模型已经学到部分下一窗口风险变化规律。",
    ],
  },
  {
    title: "LSTM 输出解释",
    items: [
      "单船页展示的预测 FPI 是模型对下一时间窗的连续风险估计值。",
      "风险等级不是模型直接输出的类别，而是将预测 FPI 经过验证集阈值校准后映射到 low / medium / high。",
      "当前前端使用的校准阈值为 0.53 / 0.69，相比默认阈值 0.40 / 0.70，能让标签准确率从 0.7821 提升到约 0.8120。",
      "页面中的“预测区间”基于验证集 RMSE 构造，用来表示预测值可能波动的大致范围；它是不确定区间，不是分类概率。",
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
          本页说明当前版本平台如何计算 FPI、ECP 与 RRI，并详细展示 1.5 阶段 LSTM 时序预测模块的样本构建、训练口径与输出解释。
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
