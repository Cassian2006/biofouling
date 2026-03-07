<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import L from "leaflet";

const props = defineProps({
  cells: {
    type: Array,
    default: () => [],
  },
  activeLayer: {
    type: String,
    default: "rri_score",
  },
  selectedHotspotKey: {
    type: String,
    default: "",
  },
  referenceSites: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["select-hotspot"]);

const mapElement = ref(null);
let map;
let tileLayer;
let gridLayer;
let referenceLayer;
let highlightLayer;

const bounds = [
  [0.8, 102.9],
  [1.85, 104.9],
];

const cellsByKey = computed(() =>
  new Map(props.cells.map((cell) => [`${cell.grid_lat}-${cell.grid_lon}`, cell])),
);

function getSpacing(values, fallback) {
  const unique = [...new Set(values.filter((value) => Number.isFinite(value)).map(Number))].sort((a, b) => a - b);
  if (unique.length < 2) return fallback;
  const diffs = [];
  for (let index = 1; index < unique.length; index += 1) {
    const diff = unique[index] - unique[index - 1];
    if (diff > 0) diffs.push(diff);
  }
  if (!diffs.length) return fallback;
  diffs.sort((a, b) => a - b);
  return diffs[Math.floor(diffs.length / 2)];
}

function getLayerValue(cell) {
  const value = cell?.[props.activeLayer];
  return Number.isFinite(value) ? Number(value) : 0;
}

function getColorScale(value, minValue, maxValue) {
  const range = Math.max(maxValue - minValue, 0.0001);
  const normalized = (value - minValue) / range;
  const hue = 186 - normalized * 154;
  const saturation = 78;
  const lightness = 84 - normalized * 36;
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

function getCellBounds(cell, latStep, lonStep) {
  const latMin = Number(cell.grid_lat) - latStep / 2;
  const latMax = Number(cell.grid_lat) + latStep / 2;
  const lonMin = Number(cell.grid_lon) - lonStep / 2;
  const lonMax = Number(cell.grid_lon) + lonStep / 2;
  return { latMin, latMax, lonMin, lonMax };
}

function toLeafletBounds(boundary) {
  return [
    [boundary.latMin, boundary.lonMin],
    [boundary.latMax, boundary.lonMax],
  ];
}

function createDisplayBounds(cell, latStep, lonStep) {
  const { latMin, latMax, lonMin, lonMax } = getCellBounds(cell, latStep, lonStep);
  const latMid = (latMin + latMax) / 2;
  const lonMid = (lonMin + lonMax) / 2;
  return [
    [
      [latMin, lonMin],
      [latMid, lonMid],
    ],
    [
      [latMin, lonMid],
      [latMid, lonMax],
    ],
    [
      [latMid, lonMin],
      [latMax, lonMid],
    ],
    [
      [latMid, lonMid],
      [latMax, lonMax],
    ],
  ];
}

function renderMap() {
  if (!map) return;

  gridLayer.clearLayers();
  referenceLayer.clearLayers();
  highlightLayer.clearLayers();

  if (!props.cells.length) return;

  const latStep = getSpacing(props.cells.map((cell) => Number(cell.grid_lat)), 0.04);
  const lonStep = getSpacing(props.cells.map((cell) => Number(cell.grid_lon)), 0.04);
  const values = props.cells.map((cell) => getLayerValue(cell));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);

  for (const cell of props.cells) {
    const value = getLayerValue(cell);
    const key = `${cell.grid_lat}-${cell.grid_lon}`;
    const displayBounds = createDisplayBounds(cell, latStep, lonStep);
    for (const displayBound of displayBounds) {
      const rectangle = L.rectangle(displayBound, {
        color: "rgba(255,255,255,0.35)",
        weight: 0.4,
        fillColor: getColorScale(value, minValue, maxValue),
        fillOpacity: 0.7,
      });
      rectangle.on("click", () => emit("select-hotspot", key));
      rectangle.bindTooltip(
        `${cell.grid_lat}, ${cell.grid_lon}<br>${props.activeLayer}: ${value.toFixed(3)}<br>RRI: ${Number(cell.rri_score || 0).toFixed(3)}`,
        { sticky: true },
      );
      rectangle.addTo(gridLayer);
    }
  }

  const selectedCell = cellsByKey.value.get(props.selectedHotspotKey);
  if (selectedCell) {
    L.rectangle(toLeafletBounds(getCellBounds(selectedCell, latStep, lonStep)), {
      color: "#1d1a16",
      weight: 2,
      fillOpacity: 0,
    }).addTo(highlightLayer);
  }

  for (const site of props.referenceSites) {
    L.circleMarker([site.latitude, site.longitude], {
      radius: 4,
      weight: 1,
      color: "#ffffff",
      fillColor: "#b45309",
      fillOpacity: 0.95,
    })
      .bindTooltip(`${site.name} (${site.site_type})`, { direction: "top" })
      .addTo(referenceLayer);
  }
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
  gridLayer = L.layerGroup().addTo(map);
  referenceLayer = L.layerGroup().addTo(map);
  highlightLayer = L.layerGroup().addTo(map);
  map.fitBounds(bounds, { padding: [16, 16] });
  renderMap();
});

watch(
  () => [props.cells, props.activeLayer, props.selectedHotspotKey, props.referenceSites],
  () => {
    renderMap();
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
  <div ref="mapElement" class="leaflet-map-stage"></div>
</template>
