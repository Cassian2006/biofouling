<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, RouterView } from "vue-router";
import MethodDrawer from "./components/MethodDrawer.vue";

const methodDrawerOpen = ref(false);
const heroPhrases = [
  "单船画像-污损诊断",
  "区域热点识别-标记",
  "维护优先级评估",
  "异常类型暴露",
];
const typedHeroText = ref("");

let activePhraseIndex = 0;
let activeCharacterIndex = 0;
let isDeleting = false;
let typewriterTimer = null;

function scheduleTypewriter(delay) {
  typewriterTimer = window.setTimeout(runTypewriter, delay);
}

function runTypewriter() {
  const phrase = heroPhrases[activePhraseIndex];
  if (!phrase) return;

  if (!isDeleting) {
    activeCharacterIndex += 1;
    typedHeroText.value = phrase.slice(0, activeCharacterIndex);
    if (activeCharacterIndex >= phrase.length) {
      isDeleting = true;
      scheduleTypewriter(1200);
      return;
    }
    scheduleTypewriter(110);
    return;
  }

  activeCharacterIndex -= 1;
  typedHeroText.value = phrase.slice(0, Math.max(activeCharacterIndex, 0));
  if (activeCharacterIndex <= 0) {
    isDeleting = false;
    activePhraseIndex = (activePhraseIndex + 1) % heroPhrases.length;
    scheduleTypewriter(240);
    return;
  }
  scheduleTypewriter(70);
}

function openMethodDrawer() {
  methodDrawerOpen.value = true;
}

function closeMethodDrawer() {
  methodDrawerOpen.value = false;
}

onMounted(() => {
  typedHeroText.value = "";
  scheduleTypewriter(320);
});

onBeforeUnmount(() => {
  if (typewriterTimer) {
    window.clearTimeout(typewriterTimer);
  }
});
</script>

<template>
  <div class="site-shell">
    <header class="site-header">
      <div class="brand-block">
        <p class="brand-kicker">Biofouling Intelligence Platform</p>
        <h1>
          船舶生物污损
          <br />
          分析平台
        </h1>
        <p class="brand-text brand-text--typewriter" aria-live="polite">
          <span class="typewriter-line">
            <span class="typewriter-prefix">平台能力：</span>
            <span class="typewriter-text">{{ typedHeroText }}</span>
            <span class="typewriter-caret" aria-hidden="true"></span>
          </span>
        </p>
      </div>

      <nav class="top-nav" aria-label="主导航">
        <RouterLink to="/" class="nav-link" active-class="active">总览 Dashboard</RouterLink>
        <RouterLink to="/vessels" class="nav-link" active-class="active">单船详情</RouterLink>
        <button type="button" class="nav-link nav-link--button" @click="openMethodDrawer">核心算法</button>
      </nav>
    </header>

    <main class="site-main">
      <RouterView />
    </main>

    <MethodDrawer :open="methodDrawerOpen" @close="closeMethodDrawer" />
  </div>
</template>
