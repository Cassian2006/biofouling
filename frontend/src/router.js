import { createRouter, createWebHistory } from "vue-router";
import DashboardPage from "./pages/DashboardPage.vue";
import VesselDetailPage from "./pages/VesselDetailPage.vue";
import RegionalRiskPage from "./pages/RegionalRiskPage.vue";

const routes = [
  {
    path: "/",
    name: "dashboard",
    component: DashboardPage,
  },
  {
    path: "/vessels/:mmsi?",
    name: "vessels",
    component: VesselDetailPage,
  },
  {
    path: "/regional-risk",
    name: "regional-risk",
    component: RegionalRiskPage,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

export default router;
