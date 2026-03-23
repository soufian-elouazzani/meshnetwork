<template>
  <div class="coverage-root">

    <!-- ── Page header (exact replica of Blazor PageHeader) ── -->
    <div class="ant-page-header">
      <div class="ant-page-header-heading">
        <div class="ant-page-header-heading-left">
          <span class="ant-page-header-heading-title">Carte de couverture</span>
          <span class="ant-page-header-heading-sub-title">
            {{ totalNodes }} nœuds avec couverture calculée — dernière mise à jour : {{ lastUpdate }}
          </span>
        </div>
        <div class="ant-page-header-heading-extra">
          <button
              class="ant-btn ant-btn-default"
              :disabled="loading"
              @click="fetchData"
          >
            <span v-if="loading" class="btn-spinner"></span>
            Actualiser
          </button>
        </div>
      </div>
      <!-- Toggles row (exact replica of PageHeaderContent) -->
      <div class="ant-page-header-content">
        <div class="toggles-row">
          <!-- Cercles de secours toggle -->
          <div
              class="ant-switch-wrapper"
              :class="{ 'ant-switch-checked': showFallbackCircles }"
              @click="showFallbackCircles = !showFallbackCircles; refreshMap()"
          >
            <button
                role="switch"
                :aria-checked="showFallbackCircles"
                class="ant-switch"
                :class="{ 'ant-switch-checked': showFallbackCircles }"
            >
              <div class="ant-switch-handle"></div>
              <span class="ant-switch-inner">
                <span class="ant-switch-inner-checked">Cercles de secours</span>
                <span class="ant-switch-inner-unchecked">Cercles de secours</span>
              </span>
            </button>
          </div>

          <!-- Marqueurs de nœuds toggle -->
          <div
              class="ant-switch-wrapper"
              :class="{ 'ant-switch-checked': showNodeMarkers }"
              @click="showNodeMarkers = !showNodeMarkers; refreshMap()"
          >
            <button
                role="switch"
                :aria-checked="showNodeMarkers"
                class="ant-switch"
                :class="{ 'ant-switch-checked': showNodeMarkers }"
            >
              <div class="ant-switch-handle"></div>
              <span class="ant-switch-inner">
                <span class="ant-switch-inner-checked">Marqueurs de nœuds</span>
                <span class="ant-switch-inner-unchecked">Marqueurs de nœuds</span>
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Map container (Spin + Osm replica) ── -->
    <div class="map-wrapper" :class="{ 'map-loading': loading }">
      <div v-if="loading" class="spin-overlay">
        <span class="spin-dot">
          <i></i><i></i><i></i><i></i>
        </span>
      </div>
      <div id="coverage-map" :style="{ height: mapHeight }"></div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import L from 'leaflet'

// ── Types ─────────────────────────────────────────────────────────────────────
interface CoverageMapDto {
  nodeId: number
  nodeName: string | null
  latitude: number | null
  longitude: number | null
  geoJson: object
  radiusMeters: number | null
  calculatedAt: string
  parameters: object | null
}

// ── State ─────────────────────────────────────────────────────────────────────
const loading             = ref(false)
const showFallbackCircles = ref(true)
const showNodeMarkers     = ref(true)
const totalNodes          = ref(0)
const lastUpdate          = ref('—')
const coverages           = ref<CoverageMapDto[]>([])

// Saved map position (localStorage — same key as Blazor)
const STORAGE_KEY = 'coverageMapPosition'
let savedLat  = 46.199144
let savedLon  = 2.321139
let savedZoom = 6

// ── Map height (same formula as Blazor: calc(100vh - 230px)) ─────────────────
const mapHeight = computed(() => {
  // When inside an iframe the full viewport IS the iframe, so 100vh works fine
  return 'calc(100vh - 230px)'
})

// ── Leaflet internals ─────────────────────────────────────────────────────────
let map: L.Map | null = null
const geojsonLayers: Record<string, L.Layer> = {}
const circleLayers:  Record<string, L.Layer> = {}
const markerLayers:  Record<string, L.Layer> = {}

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ── Map init ──────────────────────────────────────────────────────────────────
function initMap() {
  // Load saved position
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const pos = JSON.parse(raw)
      savedLat  = pos.latitude  ?? savedLat
      savedLon  = pos.longitude ?? savedLon
      savedZoom = pos.zoom      ?? savedZoom
    }
  } catch (_) { /* ignore */ }

  map = L.map('coverage-map', { preferCanvas: true })
      .setView([savedLat, savedLon], savedZoom)

  // OSM tile layer (same as Blazor maps.js default)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map)

  // Save position on move/zoom (same key as Blazor)
  map.on('moveend zoomend', () => {
    if (!map) return
    const c = map.getCenter()
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      latitude:  c.lat,
      longitude: c.lng,
      zoom:      map.getZoom()
    }))
  })
}

// ── Data fetching ─────────────────────────────────────────────────────────────
async function fetchData() {
  if (loading.value) return
  loading.value = true

  try {
    const res = await fetch(`${API_BASE}/api/coverage/all`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    coverages.value = await res.json()

    totalNodes.value = coverages.value.length
    if (coverages.value.length > 0) {
      const latest = coverages.value
          .map(c => new Date(c.calculatedAt).getTime())
          .reduce((a, b) => Math.max(a, b), 0)
      lastUpdate.value = new Date(latest).toLocaleString('fr-FR')
    } else {
      lastUpdate.value = '—'
    }
  } catch (e) {
    console.error('fetchData error', e)
  } finally {
    loading.value = false
    await renderCoverages()
  }
}

// ── Rendering ─────────────────────────────────────────────────────────────────
async function renderCoverages() {
  if (!map) return

  // Clear all existing layers
  clearLayerGroup(geojsonLayers)
  clearLayerGroup(circleLayers)
  clearLayerGroup(markerLayers)

  // 1. GeoJSON polygons — orange fill (exact same style as coverage.js)
  coverages.value.forEach(c => {
    if (!c.geoJson) return
    try {
      const layer = L.geoJSON(c.geoJson as any, {
        style: {
          color:       '#FF6600',
          weight:      2,
          opacity:     0.85,
          fillColor:   '#FF9933',
          fillOpacity: 0.15,
        }
      }).bindPopup(
          `<p><b>${esc(c.nodeName)}</b></p>` +
          `<p>Zone de couverture</p>` +
          `<p>Mis à jour : ${esc(formatDate(c.calculatedAt))}</p>`,
          { keepInView: true, autoPan: false }
      ).addTo(map!)

      geojsonLayers[`geojson-${c.nodeId}`] = layer
    } catch (e) {
      console.error(`GeoJSON error for node ${c.nodeId}`, e)
    }
  })

  // 2. Fallback circles — blue dashed (exact same style as coverage.js)
  if (showFallbackCircles.value) {
    coverages.value
        .filter(c => c.latitude != null && c.longitude != null && c.radiusMeters != null)
        .forEach(c => {
          const circle = L.circle([c.latitude!, c.longitude!], {
            radius:      c.radiusMeters!,
            color:       '#2196F3',
            weight:      1,
            opacity:     0.6,
            fillColor:   '#64B5F6',
            fillOpacity: 0.08,
            dashArray:   '6 4',
          } as any).bindPopup(
              `<p><b>${esc(c.nodeName)}</b></p>` +
              `<p>Rayon estimé : <b>${((c.radiusMeters ?? 0) / 1000).toFixed(1)} km</b></p>` +
              `<p>Calculé le : ${esc(formatDate(c.calculatedAt))}</p>`,
              { keepInView: true, autoPan: false }
          ).addTo(map!)

          circleLayers[`circle-${c.nodeId}`] = circle
        })
  }

  // 3. Node markers — blue circle markers (exact same style as Blazor circleMarker)
  if (showNodeMarkers.value) {
    coverages.value
        .filter(c => c.latitude != null && c.longitude != null)
        .forEach(c => {
          const popup =
              `<p><b>${esc(c.nodeName ?? '—')}</b></p>` +
              `<p>Portée estimée : ${c.radiusMeters != null ? ((c.radiusMeters) / 1000).toFixed(1) + ' km' : 'inconnue'}</p>` +
              `<p>Calculé le : ${esc(formatDate(c.calculatedAt))}</p>` +
              `<p><a href="/node/${c.nodeId}" target="_blank" rel="nofollow">Détail du nœud</a></p>`

          const marker = L.circleMarker([c.latitude!, c.longitude!], {
            radius:      7,
            fillOpacity: 0.2,
            color:       '#2196F3',
            fillColor:   '#2196F3',
            weight:      2,
          } as any).bindPopup(popup, {
            keepInView: true,
            closeButton: true,
            autoClose:   true,
            autoPan:     false,
          }).addTo(map!)

          markerLayers[`node-${c.nodeId}`] = marker
        })
  }
}

async function refreshMap() {
  await renderCoverages()
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function clearLayerGroup(group: Record<string, L.Layer>) {
  if (!map) return
  Object.values(group).forEach(l => map!.removeLayer(l))
  Object.keys(group).forEach(k => delete group[k])
}

function esc(str: string | null | undefined): string {
  if (!str) return ''
  return String(str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function formatDate(iso: string): string {
  try { return new Date(iso).toLocaleString('fr-FR') }
  catch (_) { return iso }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  initMap()
  await fetchData()
})

onUnmounted(() => {
  if (map) { map.off(); map.remove(); map = null }
})
</script>

<style>
/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  color: rgba(0,0,0,0.85);
}

.coverage-root {
  display: flex;
  flex-direction: column;
  padding: 0 15px 15px;
}

/* ── Page Header (Ant Design replica) ── */
.ant-page-header {
  background: #fff;
  padding: 16px 12px 12px;
  margin-bottom: 10px !important;
}

.ant-page-header-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.ant-page-header-heading-left {
  display: flex;
  flex-direction: column;
  flex-wrap: wrap;
}

.ant-page-header-heading-title {
  font-size: 20px;
  font-weight: 600;
  color: rgba(0,0,0,0.85);
  line-height: 32px;
  white-space: normal;
}

.ant-page-header-heading-sub-title {
  font-size: 14px;
  color: rgba(0,0,0,0.45);
  white-space: normal;
}

.ant-page-header-heading-extra {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ant-page-header-content {
  margin-top: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

/* ── Ant Button replica ── */
.ant-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 15px;
  font-size: 14px;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1.5715;
  height: 32px;
}
.ant-btn:hover { border-color: #4096ff; color: #4096ff; }
.ant-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-spinner {
  width: 14px; height: 14px;
  border: 2px solid #d9d9d9;
  border-top-color: #4096ff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  display: inline-block;
}

/* ── Ant Switch replica ── */
.toggles-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.ant-switch-wrapper {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.ant-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-width: 44px;
  height: 22px;
  padding: 0 8px;
  background: rgba(0,0,0,0.25);
  border: 0;
  border-radius: 100px;
  cursor: pointer;
  transition: background 0.2s;
  outline: none;
}

.ant-switch.ant-switch-checked {
  background: #1677ff;
}

.ant-switch-handle {
  position: absolute;
  left: 2px;
  width: 18px; height: 18px;
  background: #fff;
  border-radius: 50%;
  transition: left 0.2s;
  box-shadow: 0 2px 4px rgba(0,35,11,.2);
}

.ant-switch.ant-switch-checked .ant-switch-handle {
  left: calc(100% - 20px);
}

.ant-switch-inner {
  font-size: 12px;
  color: #fff;
  padding: 0 4px 0 24px;
  white-space: nowrap;
}

.ant-switch.ant-switch-checked .ant-switch-inner {
  padding: 0 24px 0 8px;
}

.ant-switch-inner-checked  { display: none; }
.ant-switch-inner-unchecked { display: inline; }

.ant-switch.ant-switch-checked .ant-switch-inner-checked  { display: inline; }
.ant-switch.ant-switch-checked .ant-switch-inner-unchecked { display: none; }

/* ── Spin overlay (Ant Design Spin replica) ── */
.map-wrapper {
  position: relative;
}

.map-loading .spin-overlay {
  display: flex;
}

.spin-overlay {
  display: none;
  position: absolute;
  inset: 0;
  z-index: 1000;
  background: rgba(255,255,255,0.5);
  align-items: center;
  justify-content: center;
}

.spin-dot {
  position: relative;
  width: 32px; height: 32px;
}

.spin-dot i {
  position: absolute;
  width: 14px; height: 14px;
  border-radius: 50%;
  background: #1677ff;
  opacity: 0.3;
  animation: antSpinMove 1s infinite linear alternate;
}

.spin-dot i:nth-child(1) { top: 0;    left: 0;   animation-delay: 0s; }
.spin-dot i:nth-child(2) { top: 0;    right: 0;  animation-delay: 0.4s; }
.spin-dot i:nth-child(3) { bottom: 0; right: 0;  animation-delay: 0.8s; }
.spin-dot i:nth-child(4) { bottom: 0; left: 0;   animation-delay: 1.2s; }

@keyframes antSpinMove {
  to { opacity: 1; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Leaflet popup tweaks (same as styles.css) ── */
.leaflet-container a { word-wrap: break-word; }

@media screen and (max-width: 576px) {
  .leaflet-popup { max-width: 200px; }
}
</style>