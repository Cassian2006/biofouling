<script setup>
import { RouterLink, RouterView } from "vue-router";
</script>

<template>
  <div class="site-shell">
    <header class="site-header">
      <div class="brand-block">
        <p class="brand-kicker">Biofouling Intelligence Platform</p>
        <h1>船舶生物污损分析平台</h1>
        <p class="brand-text">
          平台基于 AIS 航迹与海洋环境数据，面向单船暴露诊断、区域风险识别与维护优先级判读提供可视化分析界面。
        </p>
      </div>

      <nav class="top-nav" aria-label="主导航">
        <RouterLink to="/" class="nav-link" active-class="active">总览 Dashboard</RouterLink>
        <RouterLink to="/vessels" class="nav-link" active-class="active">单船详情</RouterLink>
      </nav>
    </header>

    <main class="site-main">
      <RouterView />
    </main>
  </div>
</template>
