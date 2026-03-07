import { createRouter, createWebHistory } from "vue-router";
import DashboardPage from "./pages/DashboardPage.vue";
import VesselDetailPage from "./pages/VesselDetailPage.vue";

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
    redirect: "/",
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
