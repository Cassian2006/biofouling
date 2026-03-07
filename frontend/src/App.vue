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
          平台围绕单船暴露诊断、区域风险识别与维护建议三条主线组织，当前版本已接入真实 AIS
          与环境处理结果，用于展示 1.0 阶段的完整分析闭环。
        </p>
      </div>

      <nav class="top-nav" aria-label="主导航">
        <RouterLink to="/" class="nav-link" active-class="active">总览 Dashboard</RouterLink>
        <RouterLink to="/vessels" class="nav-link" active-class="active">单船详情</RouterLink>
        <RouterLink to="/regional-risk" class="nav-link" active-class="active">区域风险</RouterLink>
      </nav>
    </header>

    <main class="site-main">
      <RouterView />
    </main>
  </div>
</template>
