<script setup>
import { computed, watch } from "vue";
import { useDemoData } from "../composables/useDemoData";

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["close"]);

const { scienceMaterials, fetchScienceMaterials } = useDemoData();

const sections = computed(() => scienceMaterials.value?.sections || []);
const title = computed(() => scienceMaterials.value?.title || "科学性说明");
const intro = computed(
  () =>
    scienceMaterials.value?.intro ||
    "本页用于说明当前平台的评分结构、科学边界与深度模块定位。",
);
const validationSummary = computed(() => scienceMaterials.value?.validation_summary || null);
const maintenanceNote = computed(() => scienceMaterials.value?.maintenance_note || "");

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      await fetchScienceMaterials();
    }
  },
  { immediate: true },
);
</script>

<template>
  <transition name="drawer-fade">
    <div v-if="open" class="method-drawer-shell" @click.self="emit('close')">
      <aside class="method-drawer" role="dialog" aria-modal="true" aria-label="核心算法说明">
        <div class="method-drawer__head">
          <div>
            <p class="section-kicker">Method</p>
            <h3>{{ title }}</h3>
          </div>
          <button type="button" class="method-drawer__close" @click="emit('close')">关闭</button>
        </div>

        <p class="method-drawer__intro">
          {{ intro }}
        </p>

        <section v-if="validationSummary" class="method-drawer__section">
          <h4>科学验证摘要</h4>
          <ul class="method-drawer__list">
            <li>当前科学评分样本分布：优先评估 {{ validationSummary.baseline_recommendation_counts["Prioritize cleaning assessment"] || 0 }}，持续监测 {{ validationSummary.baseline_recommendation_counts["Monitor exposure trend"] || 0 }}，低即时关注 {{ validationSummary.baseline_recommendation_counts["Low immediate concern"] || 0 }}。</li>
            <li>已完成 {{ validationSummary.sensitivity_scenarios }} 组敏感性分析与 {{ validationSummary.ablation_scenarios }} 组分量消融分析。</li>
            <li>最稳定的敏感性场景：{{ validationSummary.most_stable_sensitivity || "暂无" }}。</li>
            <li>当前最值得关注的分量移除场景：{{ validationSummary.most_disruptive_ablation || "暂无" }}。</li>
            <li>建议变化率最高的敏感性场景：{{ validationSummary.highest_recommendation_change_sensitivity || "暂无" }}。</li>
          </ul>
        </section>

        <section v-if="maintenanceNote" class="method-drawer__section">
          <h4>维护项口径</h4>
          <ul class="method-drawer__list">
            <li>{{ maintenanceNote }}</li>
          </ul>
        </section>

        <section v-for="section in sections" :key="section.title" class="method-drawer__section">
          <h4>{{ section.title }}</h4>
          <ul class="method-drawer__list">
            <li v-for="item in section.paragraphs" :key="item">{{ item }}</li>
          </ul>
        </section>
      </aside>
    </div>
  </transition>
</template>
