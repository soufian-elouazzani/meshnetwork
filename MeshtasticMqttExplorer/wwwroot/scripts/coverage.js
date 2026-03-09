window.coverageMap = (() => {
    const _layers = {};

    function addGeoJsonLayers(items) {
        if (!window.leafletMap) return;

        for (const id in _layers) {
            if (id.startsWith('geojson-')) {
                window.leafletMap.removeLayer(_layers[id]);
                delete _layers[id];
            }
        }

        items.forEach(item => {
            if (!item.geoJson) return;
            try {
                const layer = L.geoJSON(item.geoJson, {
                    style: {
                        color: '#FF6600', weight: 2, opacity: 0.85,
                        fillColor: '#FF9933', fillOpacity: 0.15,
                    }
                }).bindPopup(
                    `<p><b>${_esc(item.nodeName)}</b></p>` +
                    `<p>Zone de couverture</p>` +
                    `<p>Mis à jour : ${_esc(item.calcAt)}</p>`,
                    { keepInView: true, autoPan: false }
                ).addTo(window.leafletMap);

                _layers[`geojson-${item.nodeId}`] = layer;
            } catch (e) {
                console.error(`coverageMap: GeoJSON error for node ${item.nodeId}`, e);
            }
        });
    }

    function addCircles(circles) {
        if (!window.leafletMap) return;

        for (const id in _layers) {
            if (id.startsWith('circle-')) {
                window.leafletMap.removeLayer(_layers[id]);
                delete _layers[id];
            }
        }

        circles.forEach(c => {
            if (!c.latitude || !c.longitude || !c.radius) return;
            const circle = L.circle([c.latitude, c.longitude], {
                radius: c.radius,
                color: '#2196F3', weight: 1, opacity: 0.6,
                fillColor: '#64B5F6', fillOpacity: 0.08,
                dashArray: '6 4',
            }).bindPopup(
                `<p><b>${_esc(c.nodeName)}</b></p>` +
                `<p>Rayon estimé : <b>${(c.radius / 1000).toFixed(1)} km</b></p>` +
                `<p>Calculé le : ${_esc(c.calcAt)}</p>`,
                { keepInView: true, autoPan: false }
            ).addTo(window.leafletMap);

            _layers[`circle-${c.id}`] = circle;
        });
    }

    function _esc(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    return { addGeoJsonLayers, addCircles };
})();