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
  highlightedWindow: {
    type: Object,
    default: null,
  },
});

const mapElement = ref(null);
const showTrackLine = ref(true);
const showRecentSegment = ref(true);
const showLowSpeedPoints = ref(true);
const showReferencePoint = ref(true);
let map;
let tileLayer;
let trackLayer;
let recentTrackLayer;
let lowSpeedLayer;
let markerLayer;
let windowLayer;

function fitToTrack() {
  if (!map || !props.track?.points?.length) return;
  const latLngs = props.track.points.map((point) => [point.latitude, point.longitude]);
  map.fitBounds(L.latLngBounds(latLngs), { padding: [24, 24], maxZoom: 11 });
}

function renderTrack() {
  if (!map || !trackLayer || !recentTrackLayer || !lowSpeedLayer || !markerLayer || !windowLayer) return;
  trackLayer.clearLayers();
  recentTrackLayer.clearLayers();
  lowSpeedLayer.clearLayers();
  markerLayer.clearLayers();
  windowLayer.clearLayers();

  if (!props.track?.points?.length) return;

  const latLngs = props.track.points.map((point) => [point.latitude, point.longitude]);
  if (showTrackLine.value) {
    L.polyline(latLngs, {
      color: "#155e75",
      weight: 4,
      opacity: 0.95,
    }).addTo(trackLayer);
  }

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
    .addTo(markerLayer);

  L.circleMarker([endPoint.latitude, endPoint.longitude], {
    radius: 6,
    color: "#ffffff",
    weight: 2,
    fillColor: "#c2410c",
    fillOpacity: 1,
  })
    .bindTooltip("终点")
    .addTo(markerLayer);

  if (showRecentSegment.value) {
    const endTime = new Date(endPoint.timestamp).getTime();
    const recentPoints = props.track.points.filter((point) => endTime - new Date(point.timestamp).getTime() <= 24 * 3600 * 1000);
    if (recentPoints.length >= 2) {
      L.polyline(
        recentPoints.map((point) => [point.latitude, point.longitude]),
        {
          color: "#c2410c",
          weight: 5,
          opacity: 0.75,
          dashArray: "6 8",
        },
      )
        .bindTooltip("近 24 小时轨迹")
        .addTo(recentTrackLayer);
    }
  }

  if (showLowSpeedPoints.value) {
    props.track.points
      .filter((point) => point.is_low_speed)
      .slice(0, 160)
      .forEach((point) => {
        L.circleMarker([point.latitude, point.longitude], {
          radius: 3,
          color: "rgba(255,255,255,0.7)",
          weight: 1,
          fillColor: "#b45309",
          fillOpacity: 0.65,
        })
          .bindTooltip(`低速点 · ${point.timestamp}${point.sog !== null ? ` · ${point.sog} 节` : ""}`)
          .addTo(lowSpeedLayer);
      });
  }

  if (props.highlightedWindow?.start && props.highlightedWindow?.end) {
    const start = new Date(props.highlightedWindow.start).getTime();
    const end = new Date(props.highlightedWindow.end).getTime();
    const highlightedPoints = props.track.points.filter((point) => {
      const timestamp = new Date(point.timestamp).getTime();
      return timestamp >= start && timestamp < end;
    });
    if (highlightedPoints.length >= 2) {
      L.polyline(
        highlightedPoints.map((point) => [point.latitude, point.longitude]),
        {
          color: "#7c3aed",
          weight: 6,
          opacity: 0.9,
        },
      )
        .bindTooltip("当前选中时间窗")
        .addTo(windowLayer);
    }
  }

  if (props.nearestReference && showReferencePoint.value) {
    L.circleMarker([props.nearestReference.latitude, props.nearestReference.longitude], {
      radius: 5,
      color: "#ffffff",
      weight: 1,
      fillColor: "#7c3aed",
      fillOpacity: 0.9,
    })
      .bindTooltip(`${props.nearestReference.name} (${props.nearestReference.site_type})`)
      .addTo(markerLayer);
  }

  fitToTrack();
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
  L.control.scale({ imperial: false }).addTo(map);
  trackLayer = L.layerGroup().addTo(map);
  recentTrackLayer = L.layerGroup().addTo(map);
  lowSpeedLayer = L.layerGroup().addTo(map);
  markerLayer = L.layerGroup().addTo(map);
  windowLayer = L.layerGroup().addTo(map);
  map.setView([1.25, 103.9], 8);
  renderTrack();
});

watch(
  () => [props.track, props.nearestReference, props.highlightedWindow, showTrackLine.value, showRecentSegment.value, showLowSpeedPoints.value, showReferencePoint.value],
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
  <div class="track-map-shell">
    <div class="map-toolbar">
      <button type="button" class="map-toolbar__action" @click="fitToTrack">定位全轨迹</button>
      <label class="map-toolbar__toggle">
        <input v-model="showTrackLine" type="checkbox" />
        <span>主轨迹</span>
      </label>
      <label class="map-toolbar__toggle">
        <input v-model="showRecentSegment" type="checkbox" />
        <span>近 24 小时</span>
      </label>
      <label class="map-toolbar__toggle">
        <input v-model="showLowSpeedPoints" type="checkbox" />
        <span>低速点</span>
      </label>
      <label class="map-toolbar__toggle">
        <input v-model="showReferencePoint" type="checkbox" />
        <span>参考点</span>
      </label>
    </div>
    <div ref="mapElement" class="leaflet-map-stage leaflet-map-stage--track"></div>
  </div>
</template>
