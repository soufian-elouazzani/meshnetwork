<template>
  <div class="coverage-root">

    <!-- ── Page header ── -->
    <div class="ant-page-header">
      <div class="ant-page-header-heading">
        <div class="ant-page-header-heading-left">
          <span class="ant-page-header-heading-title">Carte de couverture</span>
          <span class="ant-page-header-heading-sub-title">
            {{ totalNodes }} nœuds avec couverture calculée — dernière mise à jour : {{ lastUpdate }}
          </span>
        </div>
        <div class="ant-page-header-heading-extra">
          <button class="ant-btn ant-btn-default" :disabled="loading" @click="fetchData">
            <span v-if="loading" class="btn-spinner"></span>
            Actualiser
          </button>
        </div>
      </div>

      <!-- Toggles row -->
      <div class="ant-page-header-content">
        <div class="toggles-row">
          <div
              class="ant-switch-wrapper"
              :class="{ 'ant-switch-checked': showFallbackCircles }"
              @click="showFallbackCircles = !showFallbackCircles; refreshMap()"
          >
            <button role="switch" :aria-checked="showFallbackCircles" class="ant-switch" :class="{ 'ant-switch-checked': showFallbackCircles }">
              <div class="ant-switch-handle"></div>
              <span class="ant-switch-inner">
                <span class="ant-switch-inner-checked">Cercles de secours</span>
                <span class="ant-switch-inner-unchecked">Cercles de secours</span>
              </span>
            </button>
          </div>

          <div
              class="ant-switch-wrapper"
              :class="{ 'ant-switch-checked': showNodeMarkers }"
              @click="showNodeMarkers = !showNodeMarkers; refreshMap()"
          >
            <button role="switch" :aria-checked="showNodeMarkers" class="ant-switch" :class="{ 'ant-switch-checked': showNodeMarkers }">
              <div class="ant-switch-handle"></div>
              <span class="ant-switch-inner">
                <span class="ant-switch-inner-checked">Marqueurs de nœuds</span>
                <span class="ant-switch-inner-unchecked">Marqueurs de nœuds</span>
              </span>
            </button>
          </div>

          <div
              class="ant-switch-wrapper"
              :class="{ 'ant-switch-checked': showIntersections }"
              @click="showIntersections = !showIntersections; refreshMap()"
          >
            <button role="switch" :aria-checked="showIntersections" class="ant-switch" :class="{ 'ant-switch-checked': showIntersections }">
              <div class="ant-switch-handle"></div>
              <span class="ant-switch-inner">
                <span class="ant-switch-inner-checked">Intersections</span>
                <span class="ant-switch-inner-unchecked">Intersections</span>
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Map container ── -->
    <div class="map-wrapper" :class="{ 'map-loading': loading }">
      <div v-if="loading" class="spin-overlay">
        <span class="spin-dot"><i></i><i></i><i></i><i></i></span>
      </div>
      <div id="coverage-map" :style="{ height: mapHeight }"></div>
    </div>

    <!-- ── Legend ── -->
    <div class="coverage-legend" v-if="legendItems.length > 0">
      <div class="legend-title">Légende</div>
      <div class="legend-items">
        <div v-for="item in legendItems" :key="item.label" class="legend-item">
          <span class="legend-swatch" :style="{ background: item.fill, borderColor: item.stroke }"></span>
          <span class="legend-label">{{ item.label }}</span>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import L from 'leaflet'
// @ts-ignore
import * as turf from '@turf/turf'

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

interface LegendItem {
  fill: string
  stroke: string
  label: string
}

interface OverlappingNodeDto {
  nodeId: number
  nodeName: string | null
  overlapScore: number
}

interface RedundancyDto {
  nodeId: number
  nodeName: string | null
  color: string | null
  totalScore: number
  overlapCount: number
  redundancyLevel: number
  overlappingNodes: OverlappingNodeDto[]
}

// ── Intersection color palette (index = number of overlapping nodes - 2) ──────
// index 0 = 2 nodes overlap, index 1 = 3 nodes, index 2 = 4 nodes, etc.
const INTERSECTION_COLORS: Array<{ fill: string; stroke: string }> = [
  { fill: '#2196F3', stroke: '#1565C0' }, // 2 nodes  → blue
  { fill: '#4CAF50', stroke: '#2E7D32' }, // 3 nodes  → green
  { fill: '#9C27B0', stroke: '#6A1B9A' }, // 4 nodes  → purple
  { fill: '#F44336', stroke: '#B71C1C' }, // 5 nodes  → red
  { fill: '#FF9800', stroke: '#E65100' }, // 6+ nodes → deep orange
]

function intersectionColor(overlapCount: number) {
  const idx = Math.min(overlapCount - 2, INTERSECTION_COLORS.length - 1)
  return INTERSECTION_COLORS[Math.max(0, idx)]
}

// ── State ─────────────────────────────────────────────────────────────────────
const loading             = ref(false)
const showFallbackCircles = ref(true)
const showNodeMarkers     = ref(true)
const showIntersections   = ref(true)
const totalNodes          = ref(0)
const lastUpdate          = ref('—')
const coverages           = ref<CoverageMapDto[]>([])
const legendItems         = ref<LegendItem[]>([])

const STORAGE_KEY = 'coverageMapPosition'
let savedLat  = 46.199144
let savedLon  = 2.321139
let savedZoom = 6

const mapHeight = computed(() => 'calc(100vh - 290px)')

// ── Leaflet internals ─────────────────────────────────────────────────────────
let map: L.Map | null = null
const geojsonLayers:      Record<string, L.Layer> = {}
const circleLayers:       Record<string, L.Layer> = {}
const markerLayers:       Record<string, L.Layer> = {}
const intersectionLayers: L.Layer[] = []

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ── Redundancy data (fetched once, looked up by nodeId) ───────────────────────
const redundancyMap = ref<Map<number, RedundancyDto>>(new Map())

async function fetchRedundancy() {
  try {
    const res = await fetch(`${API_BASE}/api/redundancy/all`)
    if (!res.ok) return
    const data: RedundancyDto[] = await res.json()
    redundancyMap.value = new Map(data.map(r => [r.nodeId, r]))
  } catch (e) {
    console.error('fetchRedundancy error', e)
  }
}

function redundancyLevelLabel(level: number): string {
  switch (level) {
    case 1: return 'Faible — nœud isolé'
    case 2: return 'Moyen — couverture partagée'
    case 3: return 'Bon — redondance suffisante'
    default: return `Niveau ${level}`
  }
}

function redundancyLevelColor(level: number): string {
  switch (level) {
    case 1: return '#4CAF50'
    case 2: return '#FF9800'
    default: return '#F44336'
  }
}

function buildRedundancyPopupSection(nodeId: number): string {
  const r = redundancyMap.value.get(nodeId)
  if (!r) return ''

  const overlapsHtml = r.overlappingNodes.length > 0
      ? r.overlappingNodes.map(o =>
          `<span style="display:block;padding-left:8px;color:rgba(0,0,0,0.65)">
          — ${esc(o.nodeName ?? String(o.nodeId))}
          <span style="color:#1677ff">(${(o.overlapScore * 100).toFixed(0)}%)</span>
        </span>`
      ).join('')
      : '<span style="padding-left:8px;color:rgba(0,0,0,0.45)">Aucun</span>'

  return `
    <hr style="margin:8px 0;border:none;border-top:1px solid #f0f0f0">
    <p style="font-weight:600;margin-bottom:4px">Redondance</p>
    <p>Niveau :
      <b style="color:${redundancyLevelColor(r.redundancyLevel)}">
        ${redundancyLevelLabel(r.redundancyLevel)}
      </b>
    </p>
    <p>Score total : <b>${(r.totalScore * 100).toFixed(0)}%</b></p>
    <p>Nœuds en chevauchement : <b>${r.overlapCount}</b></p>
    ${r.overlappingNodes.length > 0 ? `<p style="margin-top:4px">Avec :<br>${overlapsHtml}</p>` : ''}
  `
}

// ── Map init ──────────────────────────────────────────────────────────────────
function initMap() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const pos = JSON.parse(raw)
      savedLat  = pos.latitude  ?? savedLat
      savedLon  = pos.longitude ?? savedLon
      savedZoom = pos.zoom      ?? savedZoom
    }
  } catch (_) {}

  map = L.map('coverage-map', { preferCanvas: false })
      .setView([savedLat, savedLon], savedZoom)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map)

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
    await fetchRedundancy()
    await renderCoverages()
  }
}

// ── Intersection calculation ───────────────────────────────────────────────────
/**
 * For every pair (and higher combinations) of coverage polygons,
 * compute the intersection geometry and record how many nodes overlap there.
 *
 * Strategy:
 *   1. Build a list of valid turf features from coverages.
 *   2. For each pixel cell we track overlap count via polygon union/intersection.
 *
 * Simple O(n²) pairwise approach — good enough for typical node counts (<50).
 * We store: { geometry, nodeIds[] } for each intersection zone.
 */
interface IntersectionZone {
  geometry: object
  nodeIds: number[]
}

function computeIntersections(items: CoverageMapDto[]): IntersectionZone[] {
  // Build valid turf features
  const features: Array<{ feature: any; nodeId: number; nodeName: string }> = []

  for (const c of items) {
    if (!c.geoJson) continue
    try {
      const geoJson = c.geoJson as any
      let geom: any = null

      if (geoJson.type === 'FeatureCollection' && geoJson.features?.length > 0) {
        geom = geoJson.features[0]
      } else if (geoJson.type === 'Feature') {
        geom = geoJson
      } else if (geoJson.type === 'Polygon' || geoJson.type === 'MultiPolygon') {
        geom = { type: 'Feature', geometry: geoJson, properties: {} }
      }

      if (geom && (geom.geometry?.type === 'Polygon' || geom.geometry?.type === 'MultiPolygon')) {
        features.push({ feature: geom, nodeId: c.nodeId, nodeName: c.nodeName ?? String(c.nodeId) })
      }
    } catch (_) {}
  }

  const zones: IntersectionZone[] = []

  // Pairwise intersections
  for (let i = 0; i < features.length; i++) {
    for (let j = i + 1; j < features.length; j++) {
      try {
        const inter = turf.intersect(
            turf.featureCollection([features[i].feature, features[j].feature])
        )
        if (!inter || !inter.geometry) continue

        // Check if this intersection zone is already covered by a higher-order zone
        // For simplicity, just push it — we render highest overlap last (on top)
        zones.push({
          geometry: inter.geometry,
          nodeIds: [features[i].nodeId, features[j].nodeId],
        })
      } catch (_) {}
    }
  }

  // Now find triple+ overlaps by intersecting existing pair zones with remaining features
  // We do one more pass for triples
  const pairZones = [...zones]
  for (const zone of pairZones) {
    for (const feat of features) {
      if (zone.nodeIds.includes(feat.nodeId)) continue
      try {
        const zoneFeature = turf.feature(zone.geometry as any)
        const inter = turf.intersect(turf.featureCollection([zoneFeature, feat.feature]))
        if (!inter || !inter.geometry) continue
        const newNodeIds = [...zone.nodeIds, feat.nodeId]
        // Avoid duplicate combinations
        const key = [...newNodeIds].sort().join(',')
        const alreadyExists = zones.some(z => {
          const zKey = [...z.nodeIds].sort().join(',')
          return zKey === key
        })
        if (!alreadyExists) {
          zones.push({ geometry: inter.geometry, nodeIds: newNodeIds })
        }
      } catch (_) {}
    }
  }

  // Sort by overlap count ascending so higher overlaps render on top
  zones.sort((a, b) => a.nodeIds.length - b.nodeIds.length)

  return zones
}

// ── Rendering ─────────────────────────────────────────────────────────────────
async function renderCoverages() {
  if (!map) return

  clearLayerGroup(geojsonLayers)
  clearLayerGroup(circleLayers)
  clearLayerGroup(markerLayers)
  clearIntersectionLayers()

  // 1. Base GeoJSON polygons — orange
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
    } catch (e) {}
  })

  // 2. Intersection zones
  const usedOverlapCounts = new Set<number>()

  if (showIntersections.value && coverages.value.length >= 2) {
    const zones = computeIntersections(coverages.value)

    for (const zone of zones) {
      const overlapCount = zone.nodeIds.length
      const { fill, stroke } = intersectionColor(overlapCount)
      usedOverlapCounts.add(overlapCount)

      try {
        const nodeNames = zone.nodeIds
            .map(id => coverages.value.find(c => c.nodeId === id)?.nodeName ?? String(id))
            .join(', ')

        const layer = L.geoJSON(zone.geometry as any, {
          style: {
            color:       stroke,
            weight:      2,
            opacity:     0.9,
            fillColor:   fill,
            fillOpacity: 0.45,
          }
        }).bindPopup(
            `<p><b>Zone partagée (${overlapCount} nœuds)</b></p>` +
            `<p>${esc(nodeNames)}</p>`,
            { keepInView: true, autoPan: false }
        ).addTo(map!)

        intersectionLayers.push(layer)
      } catch (_) {}
    }
  }

  // 3. Fallback circles
  if (showFallbackCircles.value) {
    coverages.value
        .filter(c => c.latitude != null && c.longitude != null && c.radiusMeters != null)
        .forEach(c => {
          const circle = L.circle([c.latitude!, c.longitude!], {
            radius:      c.radiusMeters!,
            color:       '#607D8B',
            weight:      1,
            opacity:     0.5,
            fillColor:   '#90A4AE',
            fillOpacity: 0.05,
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

  // 4. Node markers
  if (showNodeMarkers.value) {
    coverages.value
        .filter(c => c.latitude != null && c.longitude != null)
        .forEach(c => {
          const marker = L.circleMarker([c.latitude!, c.longitude!], {
            radius:      7,
            fillOpacity: 0.9,
            color:       '#37474F',
            fillColor:   '#fff',
            weight:      2,
          } as any).addTo(map!)

          marker.on('click', () => {
            const popup =
                `<p><b>${esc(c.nodeName ?? '—')}</b></p>` +
                `<p>Portée estimée : ${c.radiusMeters != null ? ((c.radiusMeters) / 1000).toFixed(1) + ' km' : 'inconnue'}</p>` +
                `<p>Calculé le : ${esc(formatDate(c.calculatedAt))}</p>` +
                buildRedundancyPopupSection(c.nodeId) +
                `<p style="margin-top:6px"><a href="javascript:void(0)" onclick="window.__showRedundancy(${c.nodeId})">Voir détail redondance</a></p>`
            marker.bindPopup(popup, {
              keepInView: true, closeButton: true, autoClose: true, autoPan: false,
            }).openPopup()
          })
          markerLayers[`node-${c.nodeId}`] = marker
        })
  }

  // 5. Build legend
  buildLegend(usedOverlapCounts)
}

// ── Legend builder ────────────────────────────────────────────────────────────
function buildLegend(usedOverlapCounts: Set<number>) {
  const items: LegendItem[] = []

  // Always show base coverage
  items.push({ fill: '#FF9933', stroke: '#FF6600', label: 'Zone de couverture (1 nœud)' })

  // Show intersection levels that actually exist
  const sortedCounts = [...usedOverlapCounts].sort((a, b) => a - b)
  for (const count of sortedCounts) {
    const { fill, stroke } = intersectionColor(count)
    const label = count >= 6
        ? `Zone partagée (${count}+ nœuds)`
        : `Zone partagée (${count} nœuds)`
    items.push({ fill, stroke, label })
  }

  if (showFallbackCircles.value) {
    items.push({ fill: '#90A4AE', stroke: '#607D8B', label: 'Rayon estimé (cercle de secours)' })
  }

  legendItems.value = items
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

function clearIntersectionLayers() {
  if (!map) return
  intersectionLayers.forEach(l => map!.removeLayer(l))
  intersectionLayers.length = 0
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

// Expose handler globally so Leaflet popup HTML can call it
;(window as any).__showRedundancy = (nodeId: number) => {
  const r = redundancyMap.value.get(nodeId)
  if (!r) {
    const w = window.open('', '_blank')
    w?.document.write('<pre>Aucune donnée de redondance pour ce nœud.</pre>')
    return
  }
  const w = window.open('', '_blank')
  if (!w) return
  w.document.write('<pre>' + JSON.stringify(r, null, 2) + '</pre>')
  w.document.close()
}

onMounted(async () => {
  initMap()
  await fetchData()
})

onUnmounted(() => {
  if (map) { map.off(); map.remove(); map = null }
})
</script>

<style>
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

/* ── Page Header ── */
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
}

.ant-page-header-heading-sub-title {
  font-size: 14px;
  color: rgba(0,0,0,0.45);
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

/* ── Button ── */
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

/* ── Switch ── */
.toggles-row { display: flex; gap: 16px; flex-wrap: wrap; }

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

.ant-switch.ant-switch-checked { background: #1677ff; }

.ant-switch-handle {
  position: absolute;
  left: 2px;
  width: 18px; height: 18px;
  background: #fff;
  border-radius: 50%;
  transition: left 0.2s;
  box-shadow: 0 2px 4px rgba(0,35,11,.2);
}

.ant-switch.ant-switch-checked .ant-switch-handle { left: calc(100% - 20px); }

.ant-switch-inner {
  font-size: 12px;
  color: #fff;
  padding: 0 4px 0 24px;
  white-space: nowrap;
}

.ant-switch.ant-switch-checked .ant-switch-inner { padding: 0 24px 0 8px; }

.ant-switch-inner-checked  { display: none; }
.ant-switch-inner-unchecked { display: inline; }
.ant-switch.ant-switch-checked .ant-switch-inner-checked  { display: inline; }
.ant-switch.ant-switch-checked .ant-switch-inner-unchecked { display: none; }

/* ── Spin overlay ── */
.map-wrapper { position: relative; }
.map-loading .spin-overlay { display: flex; }

.spin-overlay {
  display: none;
  position: absolute;
  inset: 0;
  z-index: 1000;
  background: rgba(255,255,255,0.5);
  align-items: center;
  justify-content: center;
}

.spin-dot { position: relative; width: 32px; height: 32px; }

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

@keyframes antSpinMove { to { opacity: 1; } }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Legend ── */
.coverage-legend {
  margin-top: 12px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.legend-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(0,0,0,0.65);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(0,0,0,0.75);
}

.legend-swatch {
  display: inline-block;
  width: 20px;
  height: 14px;
  border-radius: 3px;
  border: 2px solid;
  opacity: 0.85;
  flex-shrink: 0;
}

/* ── Leaflet popup tweaks ── */
.leaflet-container a { word-wrap: break-word; }

@media screen and (max-width: 576px) {
  .leaflet-popup { max-width: 200px; }
  .legend-items { gap: 8px 16px; }
}
</style>