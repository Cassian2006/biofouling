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
      "当前版本输出的是可解释的风险代理指标，不直接声称等于真实污损厚度。",
      "FPI 用来看单船污损倾向，ECP 用来看潜在排放惩罚，RRI 用来看区域综合风险。",
      "1.5 阶段新增 LSTM 时序预测，用来补充“下一时间窗可能怎样”，不替代当前规则结果。",
    ],
  },
  {
    title: "FPI 计算",
    items: [
      "FPI = 0.5 × 行为情况 + 0.3 × 海水条件 + 0.2 × 维护间隔。",
      "行为情况 = 0.35 × 停留时长 + 0.30 × 锚泊时长 + 0.20 × 低速时长 + 0.15 × 港口访问次数。",
      "这些行为项都会先归一化，再压到 0 到 1 之间。",
    ],
  },
  {
    title: "海水条件与 ECP",
    items: [
      "海水条件 = 0.55 × 海表温度 + 0.45 × 叶绿素。",
      "海温使用 24°C 到 32°C 做归一化；叶绿素以 1.5 作为上限。",
      "ECP 以 FPI 为基础，再按暖水、高叶绿素和长时间低速做倍率修正。",
      "若平均海温 >= 28°C，ECP 增加 15%；叶绿素 >= 0.5 增加 10%；低速时长 >= 48 小时再增加 5%。",
    ],
  },
  {
    title: "RRI 计算",
    items: [
      "RRI = 0.40 × 海水条件 + 0.25 × 船多不多 + 0.20 × 锚地压力 + 0.15 × 行为情况。",
      "船多不多，指的是这一格网里船流是否密集；停得久不久，指的是船是否经常低速或停留。",
      "RRI 主要用于找区域热点，所以更看重海水条件、船流和锚地压力。",
    ],
  },
  {
    title: "LSTM 数据构建",
    items: [
      "预测模块先把清洗后的 AIS 和环境匹配结果按 6 小时窗口聚合，形成窗口级行为与环境特征。",
      "每个窗口保留 ping_count、coverage_ratio、mean_sog、max_sog、low_speed_ratio、mean_sst、mean_chlorophyll_a、mean_salinity、mean_current_u、mean_current_v 与当前窗口 FPI proxy。",
      "训练样本使用最近 8 个连续窗口作为输入，预测下一个窗口的 FPI proxy。",
      "当前 15 天真实窗口上共生成 5495 条窗口记录和 1160 条监督式序列样本。",
    ],
  },
  {
    title: "LSTM 训练流程",
    items: [
      "模型采用轻量单层 LSTM，hidden size 为 32，按船舶划分训练集与验证集。",
      "训练目标是回归下一窗口的连续 FPI proxy，而不是直接做三分类。",
      "当前保留基线模型，因为简单平衡版虽然改变了标签分布表现，但整体误差和稳定性不如基线。",
      "当前验证结果约为 MAE 0.1629、RMSE 0.2111、R² 0.5254。",
    ],
  },
  {
    title: "LSTM 输出解释",
    items: [
      "单船页显示的预测 FPI，是模型对下一时间窗的连续风险估计值。",
      "风险等级不是模型直接输出的类别，而是将预测 FPI 经过验证集阈值校准后映射到 low / medium / high。",
      "当前前端使用的校准阈值为 0.53 / 0.69。",
      "页面中的“预测区间”表示预测值可能波动的范围，不是概率。",
    ],
  },
  {
    title: "建议判定",
    items: [
      "若 FPI >= 0.70 或 ECP >= 0.85，建议优先评估清洗。",
      "若 FPI >= 0.40 或 ECP >= 0.55，建议持续监测趋势。",
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
          本页说明当前版本平台如何计算 FPI、ECP 与 RRI，并介绍 1.5 阶段 LSTM 时序预测模块的样本构建、训练口径与输出解释。
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
