<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import L from "leaflet";

const props = defineProps({
  track: {
    type: Object,
    default: null,
  },
  nearestReference: {
    type: Object,
    default: null,
  },
});

const mapElement = ref(null);
let map;
let tileLayer;
let trackLayer;

function renderTrack() {
  if (!map || !trackLayer) return;
  trackLayer.clearLayers();

  if (!props.track?.points?.length) return;

  const latLngs = props.track.points.map((point) => [point.latitude, point.longitude]);
  L.polyline(latLngs, {
    color: "#155e75",
    weight: 4,
    opacity: 0.95,
  }).addTo(trackLayer);

  const startPoint = props.track.points[0];
  const endPoint = props.track.points[props.track.points.length - 1];

  L.circleMarker([startPoint.latitude, startPoint.longitude], {
    radius: 6,
    color: "#ffffff",
    weight: 2,
    fillColor: "#0f766e",
    fillOpacity: 1,
  })
    .bindTooltip("起点")
    .addTo(trackLayer);

  L.circleMarker([endPoint.latitude, endPoint.longitude], {
    radius: 6,
    color: "#ffffff",
    weight: 2,
    fillColor: "#c2410c",
    fillOpacity: 1,
  })
    .bindTooltip("终点")
    .addTo(trackLayer);

  props.track.points
    .filter((point) => point.is_low_speed)
    .slice(0, 120)
    .forEach((point) => {
      L.circleMarker([point.latitude, point.longitude], {
        radius: 3,
        color: "rgba(255,255,255,0.7)",
        weight: 1,
        fillColor: "#b45309",
        fillOpacity: 0.65,
      }).addTo(trackLayer);
    });

  if (props.nearestReference) {
    L.circleMarker([props.nearestReference.latitude, props.nearestReference.longitude], {
      radius: 5,
      color: "#ffffff",
      weight: 1,
      fillColor: "#7c3aed",
      fillOpacity: 0.9,
    })
      .bindTooltip(`${props.nearestReference.name} (${props.nearestReference.site_type})`)
      .addTo(trackLayer);
  }

  map.fitBounds(L.latLngBounds(latLngs), { padding: [24, 24], maxZoom: 11 });
}

onMounted(() => {
  map = L.map(mapElement.value, {
    zoomControl: true,
    attributionControl: true,
  });
  tileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  trackLayer = L.layerGroup().addTo(map);
  map.setView([1.25, 103.9], 8);
  renderTrack();
});

watch(
  () => [props.track, props.nearestReference],
  () => {
    renderTrack();
  },
  { deep: true },
);

onBeforeUnmount(() => {
  if (map) {
    map.remove();
  }
});
</script>

<template>
  <div ref="mapElement" class="leaflet-map-stage leaflet-map-stage--track"></div>
</template>
