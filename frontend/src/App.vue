<script setup>
import { RouterLink, RouterView } from "vue-router";
</script>

<template>
  <div class="site-shell">
    <header class="site-header">
      <div class="brand-block">
        <p class="brand-kicker">Biofouling Intelligence</p>
        <h1>船舶生物污损分析平台</h1>
        <p class="brand-text">
          当前原型按三个正式页面组织：总览 Dashboard、单船详情页、区域风险页。
          现在它已经不只是展示架子，而是能直接读取真实 AIS 和环境处理结果的前后端应用。
        </p>
      </div>

      <nav class="top-nav" aria-label="主导航">
        <RouterLink to="/" class="nav-link" active-class="active">总览 Dashboard</RouterLink>
        <RouterLink to="/vessels" class="nav-link" active-class="active">单船详情页</RouterLink>
        <RouterLink to="/regional-risk" class="nav-link" active-class="active">区域风险页</RouterLink>
      </nav>
    </header>

    <main class="site-main">
      <RouterView />
    </main>
  </div>
</template>
