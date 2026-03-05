/* ─── Rowalyse Client-Side JavaScript ─────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
    initDropdownNavs();
    initToggle();
    initSplitSections();
    initFormSubmit();
    initSharkModal();
});


// ─── Direct Dropdown Selection ───────────────────────────────────

function initDropdownNavs() {
    const pastSelect = document.getElementById('past_select');
    if (pastSelect) {
        pastSelect.addEventListener('change', () => {
            if (pastSelect.value) {
                window.location.href = pastSelect.value;
            }
        });
    }

    const recentSelect = document.getElementById('recent_select');
    const urlInput = document.getElementById('activity_url');
    if (recentSelect && urlInput) {
        recentSelect.addEventListener('change', () => {
            if (recentSelect.value) {
                urlInput.value = recentSelect.value;

                urlInput.focus();
                // Brief highlight effect
                urlInput.style.borderColor = '#3b82f6';
                urlInput.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.15)';
                setTimeout(() => {
                    urlInput.style.borderColor = '';
                    urlInput.style.boxShadow = '';
                }, 1500);
            }
        });
    }
}


// ─── Interval Mode Toggle ──────────────────────────────────────

function initToggle() {
    const radios = document.querySelectorAll('input[name="interval_mode"]');
    const timeFields = document.getElementById('time-fields');
    const distFields = document.getElementById('distance-fields');
    const countFields = document.getElementById('count-fields');

    if (!radios.length || !timeFields || !distFields || !countFields) return;

    radios.forEach(radio => {
        radio.addEventListener('change', () => {
            if (radio.value === 'time') {
                timeFields.classList.remove('hidden');
                distFields.classList.add('hidden');
                countFields.classList.remove('hidden');
            } else if (radio.value === 'distance') {
                timeFields.classList.add('hidden');
                distFields.classList.remove('hidden');
                countFields.classList.remove('hidden');
            } else if (radio.value === 'full') {
                timeFields.classList.add('hidden');
                distFields.classList.add('hidden');
                countFields.classList.add('hidden');
            }
        });
    });
}


// ─── Collapsible 500m Split Sections ───────────────────────────

function initSplitSections() {
    const toggles = document.querySelectorAll('.split-toggle');

    toggles.forEach((toggle, index) => {
        const section = toggle.closest('.split-section');

        if (index === 0 && section) {
            section.classList.add('open');
        }

        toggle.addEventListener('click', () => {
            section.classList.toggle('open');
        });
    });
}


// ─── Form Submit Loading State ─────────────────────────────────

function initFormSubmit() {
    const form = document.getElementById('analyze-form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
        const btn = document.getElementById('analyze-btn');
        const btnText = btn.querySelector('.btn-text');
        const btnLoading = btn.querySelector('.btn-loading');

        if (btnText && btnLoading) {
            btnText.classList.add('hidden');
            btnLoading.classList.remove('hidden');
        }
        btn.disabled = true;
    });
}


// ─── Chart.js Graphs ───────────────────────────────────────────

const CHART_COLORS = [
    '#3b82f6',  // blue
    '#10b981',  // green
    '#f59e0b',  // amber
    '#ef4444',  // red
    '#8b5cf6',  // purple
    '#ec4899',  // pink
];

function initCharts(chartData) {
    if (!chartData || !chartData.length) return;

    const speedCtx = document.getElementById('speed-chart');
    if (speedCtx) createSpeedChart(speedCtx, chartData);

    const cadenceCtx = document.getElementById('cadence-chart');
    if (cadenceCtx) createCadenceChart(cadenceCtx, chartData);

    const hrCtx = document.getElementById('heartrate-chart');
    if (hrCtx) createHeartrateChart(hrCtx, chartData);
}

function createSpeedChart(ctx, chartData) {
    const datasets = chartData.map((interval, i) => ({
        label: interval.label,
        data: interval.points
            .filter(p => p.split !== null && p.split < 300)
            .map(p => ({ x: p.distance, y: p.split })),
        borderColor: CHART_COLORS[i % CHART_COLORS.length],
        backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + '15',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: true,
    }));

    new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', font: { size: 12, family: 'Inter' } },
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const v = ctx.parsed.y;
                            const m = Math.floor(v / 60);
                            const s = (v - m * 60).toFixed(1);
                            return `${ctx.dataset.label}: ${m}:${s.padStart(4, '0')}/500m`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Distance (m)', font: { size: 12, family: 'Inter' } },
                    ticks: { font: { size: 11, family: 'Inter' } },
                    grid: { color: '#f0f0f0' },
                },
                y: {
                    reverse: true,
                    title: { display: true, text: 'Split /500m (s)', font: { size: 12, family: 'Inter' } },
                    ticks: {
                        font: { size: 11, family: 'Inter' },
                        callback: (v) => {
                            const m = Math.floor(v / 60);
                            const s = Math.round(v - m * 60);
                            return `${m}:${s.toString().padStart(2, '0')}`;
                        },
                    },
                    grid: { color: '#f0f0f0' },
                },
            },
        },
    });
}

function createCadenceChart(ctx, chartData) {
    const datasets = chartData.map((interval, i) => ({
        label: interval.label,
        data: interval.points
            .filter(p => p.cadence > 0)
            .map(p => ({ x: p.distance, y: p.cadence })),
        borderColor: CHART_COLORS[i % CHART_COLORS.length],
        backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + '15',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: true,
    }));

    new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', font: { size: 12, family: 'Inter' } },
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y} spm`,
                    },
                },
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Distance (m)', font: { size: 12, family: 'Inter' } },
                    ticks: { font: { size: 11, family: 'Inter' } },
                    grid: { color: '#f0f0f0' },
                },
                y: {
                    title: { display: true, text: 'Cadence (spm)', font: { size: 12, family: 'Inter' } },
                    ticks: { font: { size: 11, family: 'Inter' } },
                    grid: { color: '#f0f0f0' },
                },
            },
        },
    });
}

function createHeartrateChart(ctx, chartData) {
    const datasets = chartData.map((interval, i) => ({
        label: interval.label,
        data: interval.points
            .filter(p => p.heartrate && p.heartrate > 0)
            .map(p => ({ x: p.distance, y: p.heartrate })),
        borderColor: CHART_COLORS[i % CHART_COLORS.length],
        backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + '15',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: true,
    }));

    // Only render if there's actually heartrate data
    const hasData = datasets.some(d => d.data.length > 0);
    if (!hasData) {
        ctx.closest('.chart-container').style.display = 'none';
        return;
    }

    new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', font: { size: 12, family: 'Inter' } },
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y} bpm`,
                    },
                },
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'Distance (m)', font: { size: 12, family: 'Inter' } },
                    ticks: { font: { size: 11, family: 'Inter' } },
                    grid: { color: '#f0f0f0' },
                },
                y: {
                    title: { display: true, text: 'Heart Rate (bpm)', font: { size: 12, family: 'Inter' } },
                    ticks: { font: { size: 11, family: 'Inter' } },
                    grid: { color: '#f0f0f0' },
                },
            },
        },
    });
}


// ─── Wind Map (Windfinder-style) ───────────────────────────────

function initWindMap(speedKn, directionDeg, lat, lng) {
    const container = document.getElementById('wind-map');
    if (!container || typeof L === 'undefined') return;

    const map = L.map(container, {
        center: [lat, lng],
        zoom: 14,
        zoomControl: false,
        attributionControl: false,
        dragging: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        touchZoom: false,
    });

    // Muted blue-tinted tile layer (similar to Windfinder's style)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
    }).addTo(map);

    // Blue overlay for Windfinder atmosphere
    const overlay = L.rectangle(map.getBounds().pad(1), {
        color: 'transparent',
        fillColor: '#3b5a8a',
        fillOpacity: 0.35,
    }).addTo(map);

    // Windfinder-style color scale (kn thresholds)
    function windColor(kn) {
        if (kn <= 1) return '#c8e6ff';
        if (kn <= 3) return '#96c8f0';
        if (kn <= 7) return '#64b4e6';
        if (kn <= 11) return '#3c9edc';
        if (kn <= 15) return '#28c83c';
        if (kn <= 19) return '#1eaa2d';
        if (kn <= 23) return '#ffd700';
        if (kn <= 27) return '#ffa500';
        if (kn <= 31) return '#ff6600';
        if (kn <= 35) return '#ff3300';
        if (kn <= 39) return '#e60000';
        if (kn <= 43) return '#cc00cc';
        if (kn <= 47) return '#9900cc';
        if (kn <= 51) return '#6600cc';
        return '#330066';
    }

    // Canvas overlay for wind arrows
    const WindCanvas = L.Layer.extend({
        onAdd(map) {
            this._map = map;
            const canvas = L.DomUtil.create('canvas', 'wind-canvas');
            const size = map.getSize();
            canvas.width = size.x;
            canvas.height = size.y;
            canvas.style.position = 'absolute';
            canvas.style.top = '0';
            canvas.style.left = '0';
            canvas.style.pointerEvents = 'none';
            map.getPanes().overlayPane.appendChild(canvas);
            this._canvas = canvas;
            this._draw();
        },
        onRemove() {
            if (this._canvas) this._canvas.remove();
        },
        _draw() {
            const ctx = this._canvas.getContext('2d');
            const w = this._canvas.width;
            const h = this._canvas.height;
            ctx.clearRect(0, 0, w, h);

            const color = windColor(speedKn);
            // Wind direction in meteorological convention:
            // directionDeg = where wind comes FROM.
            // Arrow should point in the direction wind is going TO.
            const rad = ((directionDeg + 180) % 360) * Math.PI / 180;

            const spacing = 48;
            const arrowLen = 18;
            const headLen = 6;

            for (let x = spacing / 2; x < w; x += spacing) {
                for (let y = spacing / 2; y < h; y += spacing) {
                    const ex = x + Math.sin(rad) * arrowLen;
                    const ey = y - Math.cos(rad) * arrowLen;

                    ctx.beginPath();
                    ctx.moveTo(x, y);
                    ctx.lineTo(ex, ey);
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 2;
                    ctx.stroke();

                    // Arrowhead
                    const angle = Math.atan2(ey - y, ex - x);
                    ctx.beginPath();
                    ctx.moveTo(ex, ey);
                    ctx.lineTo(
                        ex - headLen * Math.cos(angle - Math.PI / 6),
                        ey - headLen * Math.sin(angle - Math.PI / 6)
                    );
                    ctx.moveTo(ex, ey);
                    ctx.lineTo(
                        ex - headLen * Math.cos(angle + Math.PI / 6),
                        ey - headLen * Math.sin(angle + Math.PI / 6)
                    );
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 2;
                    ctx.stroke();
                }
            }

            // Speed label
            ctx.fillStyle = 'rgba(255,255,255,0.85)';
            ctx.fillRect(w - 70, h - 28, 62, 22);
            ctx.fillStyle = color;
            ctx.font = 'bold 12px Inter, sans-serif';
            ctx.fillText(speedKn + ' kn', w - 64, h - 12);
        },
    });

    new WindCanvas().addTo(map);
}


// ─── Activity Map (Polyline) ───────────────────────────────────

function decodePolyline(encoded) {
    if (!encoded) return [];
    var poly = [];
    var index = 0, len = encoded.length;
    var lat = 0, lng = 0;

    while (index < len) {
        var b, shift = 0, result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        var dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
        lat += dlat;

        shift = 0;
        result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        var dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
        lng += dlng;

        poly.push([lat * 1e-5, lng * 1e-5]);
    }
    return poly;
}

function initActivityMap(polylineStr) {
    const container = document.getElementById('activity-map');
    if (!container || typeof L === 'undefined' || !polylineStr) return;

    const coords = decodePolyline(polylineStr);
    if (!coords || coords.length === 0) return;

    const map = L.map(container, {
        zoomControl: false,
        attributionControl: false,
        scrollWheelZoom: false,
        touchZoom: false,
        dragging: false,
        doubleClickZoom: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
    }).addTo(map);

    const routeLine = L.polyline(coords, {
        color: '#fc4c02',
        weight: 4,
        opacity: 0.8,
        lineJoin: 'round'
    }).addTo(map);

    L.circleMarker(coords[0], {
        radius: 5, fillColor: '#10b981', color: '#fff', weight: 2, fillOpacity: 1
    }).addTo(map);

    L.circleMarker(coords[coords.length - 1], {
        radius: 5, fillColor: '#111', color: '#fff', weight: 2, fillOpacity: 1
    }).addTo(map);

    map.fitBounds(routeLine.getBounds(), { padding: [15, 15] });
}


// ─── Stats Chart (Homepage) ────────────────────────────────────

function initStatsChart(data) {
    const ctx = document.getElementById('stats-chart');
    if (!ctx || !data || !data.length) return;

    // Fill in missing dates between first data point and today
    const filled = [];

    // Parse the first date correctly without timezone shift
    const startParts = data[0].date.split('-');
    const start = new Date(startParts[0], startParts[1] - 1, startParts[2]);

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dateMap = {};
    data.forEach(d => dateMap[d.date] = d.count);

    for (let d = new Date(start); d <= today; d.setDate(d.getDate() + 1)) {
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        const key = `${yyyy}-${mm}-${dd}`;
        filled.push({ date: key, count: dateMap[key] || 0 });
    }

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: filled.map(d => d.date),
            datasets: [{
                label: 'Sessions',
                data: filled.map(d => d.count),
                backgroundColor: '#3b82f680',
                borderColor: '#3b82f6',
                borderWidth: 1,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    ticks: {
                        font: { size: 10, family: 'Inter' },
                        maxTicksLimit: 7,
                    },
                    grid: { display: false },
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: { size: 10, family: 'Inter' },
                        stepSize: 1,
                    },
                    grid: { color: '#f0f0f0' },
                },
            },
        },
    });
}


// ─── Shark Mode ────────────────────────────────────────────────

function initSharkModal() {
    const btn = document.getElementById('shark-btn');
    const modal = document.getElementById('shark-modal');
    const close = document.getElementById('shark-close');
    const bookmarklet = document.getElementById('shark-bookmarklet');

    if (!btn || !modal) return;

    // Detect mobile and toggle visibility
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const desktopMethod = document.getElementById('shark-desktop-method');
    const mobileMethod = document.getElementById('shark-mobile-method');

    if (desktopMethod && mobileMethod) {
        if (isMobile) {
            desktopMethod.style.display = 'none';
            mobileMethod.style.display = 'block';
        } else {
            desktopMethod.style.display = 'block';
            mobileMethod.style.display = 'none';
        }
    }

    // Generate self-contained bookmarklet that shows its own config dialog on Strava
    if (bookmarklet) {
        const serverUrl = window.location.origin;

        // Build the bookmarklet script that creates an in-page config dialog
        const bmCode = `javascript:void(function(){` +
            `if(!location.href.match(/strava\\.com\\/activities\\/(\\d+)/)){alert('Open a Strava activity page first!');return;}` +
            `var id=location.href.match(/\\/activities\\/(\\d+)/)[1];` +
            `var title=document.title||'Activity';` +
            // Create overlay
            `var o=document.createElement('div');` +
            `o.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:99999;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,Inter,sans-serif;';` +
            // Build dialog HTML
            `o.innerHTML='` +
            `<div style="background:#fff;padding:24px;border-radius:14px;width:340px;max-width:90vw;box-shadow:0 12px 40px rgba(0,0,0,.2);">` +
            `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">` +
            `<div style="font-size:1.15rem;font-weight:700;">🦈 Rowalyse</div>` +
            `<button id="_rc" style="background:none;border:none;font-size:1.4rem;cursor:pointer;color:#999;padding:0 4px;">×</button>` +
            `</div>` +
            // Interval type
            `<div style="margin-bottom:12px;">` +
            `<div style="font-size:.8rem;font-weight:500;color:#666;margin-bottom:4px;">Interval Type</div>` +
            `<div style="display:flex;border:1.5px solid #e5e7eb;border-radius:8px;overflow:hidden;">` +
            `<label style="flex:1;text-align:center;cursor:pointer;"><input type="radio" name="_rm" value="time" checked style="display:none;"><span id="_rmt" style="display:block;padding:8px;font-size:.8rem;font-weight:500;background:#3b82f6;color:#fff;">Time</span></label>` +
            `<label style="flex:1;text-align:center;cursor:pointer;"><input type="radio" name="_rm" value="distance" style="display:none;"><span id="_rmd" style="display:block;padding:8px;font-size:.8rem;font-weight:500;color:#666;border-left:1px solid #e5e7eb;">Distance</span></label>` +
            `<label style="flex:1;text-align:center;cursor:pointer;"><input type="radio" name="_rm" value="full" style="display:none;"><span id="_rmf" style="display:block;padding:8px;font-size:.8rem;font-weight:500;color:#666;border-left:1px solid #e5e7eb;">Full</span></label>` +
            `</div></div>` +
            // Time fields
            `<div id="_rtf" style="display:flex;gap:8px;margin-bottom:12px;">` +
            `<div style="flex:1;"><div style="font-size:.75rem;color:#888;margin-bottom:2px;">Minutes</div><input id="_rmn" type="number" value="4" min="0" max="60" style="width:100%;padding:7px;border:1.5px solid #e5e7eb;border-radius:6px;font-size:.9rem;"></div>` +
            `<div style="flex:1;"><div style="font-size:.75rem;color:#888;margin-bottom:2px;">Seconds</div><input id="_rsc" type="number" value="50" min="0" max="59" style="width:100%;padding:7px;border:1.5px solid #e5e7eb;border-radius:6px;font-size:.9rem;"></div>` +
            `</div>` +
            // Distance field
            `<div id="_rdf" style="display:none;margin-bottom:12px;">` +
            `<div style="font-size:.75rem;color:#888;margin-bottom:2px;">Distance (meters)</div>` +
            `<input id="_rds" type="number" value="2000" min="100" style="width:100%;padding:7px;border:1.5px solid #e5e7eb;border-radius:6px;font-size:.9rem;">` +
            `</div>` +
            // Count + cadence
            `<div id="_rcf" style="display:flex;gap:8px;margin-bottom:16px;">` +
            `<div style="flex:1;"><div style="font-size:.75rem;color:#888;margin-bottom:2px;">Intervals</div><input id="_rcn" type="number" value="3" min="1" max="20" style="width:100%;padding:7px;border:1.5px solid #e5e7eb;border-radius:6px;font-size:.9rem;"></div>` +
            `<div style="flex:1;"><div style="font-size:.75rem;color:#888;margin-bottom:2px;">Min Cadence</div><input id="_rcd" type="number" value="24" min="0" style="width:100%;padding:7px;border:1.5px solid #e5e7eb;border-radius:6px;font-size:.9rem;"></div>` +
            `</div>` +
            // Analyse button
            `<button id="_rgo" style="width:100%;padding:11px;background:#1e3a5f;color:#fff;border:none;border-radius:8px;font-size:.95rem;font-weight:600;cursor:pointer;">🦈 Analyse</button>` +
            `</div>` +
            `';` +
            `document.body.appendChild(o);` +
            // Toggle time/distance/full
            `document.querySelectorAll('input[name=_rm]').forEach(function(r){r.onchange=function(){` +
            `var t=r.value==='time';` +
            `var d=r.value==='distance';` +
            `var f=r.value==='full';` +
            `document.getElementById('_rtf').style.display=t?'flex':'none';` +
            `document.getElementById('_rdf').style.display=d?'block':'none';` +
            `document.getElementById('_rcf').style.display=f?'none':'flex';` +
            `document.getElementById('_rmt').style.cssText='display:block;padding:8px;font-size:.8rem;font-weight:500;'+(t?'background:#3b82f6;color:#fff;':'color:#666;');` +
            `document.getElementById('_rmd').style.cssText='display:block;padding:8px;font-size:.8rem;font-weight:500;border-left:1px solid #e5e7eb;'+(d?'background:#3b82f6;color:#fff;':'color:#666;');` +
            `document.getElementById('_rmf').style.cssText='display:block;padding:8px;font-size:.8rem;font-weight:500;border-left:1px solid #e5e7eb;'+(f?'background:#3b82f6;color:#fff;':'color:#666;');` +
            `};});` +
            // Close
            `document.getElementById('_rc').onclick=function(){o.remove();};` +
            `o.onclick=function(e){if(e.target===o)o.remove();};` +
            // Analyse
            `document.getElementById('_rgo').onclick=function(){` +
            `var btn=document.getElementById('_rgo');` +
            `btn.textContent='Fetching...';btn.disabled=true;` +
            `var mode=document.querySelector('input[name=_rm]:checked').value;` +
            `var types='time,velocity_smooth,cadence,distance,heartrate';` +
            `fetch('/api/v3/activities/'+id+'/streams?keys='+types+'&key_by_type=true',{credentials:'include'})` +
            `.then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json()})` +
            `.then(function(data){` +
            `var form=document.createElement('form');` +
            `form.method='POST';form.action='${serverUrl}/shark/receive';` +
            `var fields={streams:JSON.stringify(data),activity_url:location.href,activity_name:title,` +
            `interval_mode:mode,` +
            `interval_minutes:document.getElementById('_rmn').value,` +
            `interval_seconds:document.getElementById('_rsc').value,` +
            `interval_distance:document.getElementById('_rds').value,` +
            `num_intervals:document.getElementById('_rcn').value,` +
            `min_cadence:document.getElementById('_rcd').value};` +
            `for(var k in fields){var inp=document.createElement('input');inp.type='hidden';inp.name=k;inp.value=fields[k];form.appendChild(inp);}` +
            `document.body.appendChild(form);form.submit();` +
            `})` +
            `.catch(function(e){btn.textContent='🦈 Analyse';btn.disabled=false;alert('Failed: '+e.message+'\\n\\nMake sure you are logged into Strava and can see this activity.');});` +
            `};` +
            `}())`;

        bookmarklet.href = bmCode;
    }

    btn.addEventListener('click', (e) => {
        e.preventDefault();
        modal.classList.remove('hidden');
    });

    close.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });

    // iPhone: copy bookmarklet code to clipboard
    const copyBtn = document.getElementById('copy-shark-code');
    if (copyBtn && bookmarklet) {
        copyBtn.addEventListener('click', () => {
            const code = bookmarklet.href;
            navigator.clipboard.writeText(code).then(() => {
                const status = document.getElementById('copy-shark-status');
                if (status) {
                    status.textContent = ' ✓ Copied!';
                    status.style.color = '#10b981';
                    setTimeout(() => { status.textContent = ''; }, 2500);
                }
            }).catch(() => {
                // Fallback
                const ta = document.createElement('textarea');
                ta.value = bookmarklet.href;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                const status = document.getElementById('copy-shark-status');
                if (status) {
                    status.textContent = ' ✓ Copied!';
                    status.style.color = '#10b981';
                    setTimeout(() => { status.textContent = ''; }, 2500);
                }
            });
        });
    }
}


// ─── Share Link ────────────────────────────────────────────────

function copyShareLink(url) {
    navigator.clipboard.writeText(url).then(() => {
        showToast('Link copied! 📋');
    }).catch(() => {
        // Fallback for older browsers
        const input = document.createElement('input');
        input.value = url;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
        showToast('Link copied! 📋');
    });
}

function showToast(message) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 2500);
}


// ─── Dropdown ──────────────────────────────────────────────────

function toggleDropdown(id) {
    const el = document.getElementById(id);
    el.classList.toggle('hidden');

    // Close on outside click
    const close = (e) => {
        if (!el.contains(e.target) && !e.target.closest('.save-group-dropdown')) {
            el.classList.add('hidden');
            document.removeEventListener('click', close);
        }
    };
    setTimeout(() => document.addEventListener('click', close), 10);
}


// ─── Did I Do Great ────────────────────────────────────────────

const COMPLIMENTS = [
    { emoji: "⚡", title: "Wattage Bazooka!", text: "Are you a nuclear reactor? Because you were generating some serious watts out there! ☢️" },
    { emoji: "🚀", title: "Absolute Unit!", text: "Your splits are dropping faster than my jaw. You're a machine! 🤯" },
    { emoji: "🥇", title: "World-Class Power!", text: "Is your name Sinkovic? Because that was world-class power application! 🇭🇷" },
    { emoji: "🌊", title: "Water Bender!", text: "The water called. It asked you to go a little easier on it next time. 🔥" },
    { emoji: "💰", title: "Farming Watts!", text: "If watts were dollars, you'd be Jeff Bezos right now. Keep farming! 🦵" },
    { emoji: "💥", title: "Erg Crusher!", text: "Erg screens fear you. Excellent pacing and massive power output! 🖥️" },
    { emoji: "🚤", title: "Hydroplaning!", text: "You're pulling so hard, I'm surprised the boat didn't start hydroplaning. 💦" },
    { emoji: "🚂", title: "The Engine Room!", text: "Forget the engine room, you ARE the engine room. Phenomenal work! 😤" },
    { emoji: "⏱️", title: "Metronome Mode!", text: "Your cadence is so consistent it makes a metronome look rhythmically challenged. 💯" },
    { emoji: "🎓", title: "Masterclass!", text: "That wasn't just rowing; that was a masterclass in aquatic domination. 💧" },
    { emoji: "🌪️", title: "Hurricane Force!", text: "I've seen less power generated by a wind turbine in a hurricane. ⚡" },
    { emoji: "🧈", title: "Smooth & Fast!", text: "They say smooth is fast. You must be butter, because you were flying! 🚀" },
    { emoji: "🔊", title: "Noise Complaint!", text: "With those splits, the fish are definitely filing a noise complaint. 🐟" },
    { emoji: "🌍", title: "Tide Turner!", text: "You pushed the water back so hard, the tide just changed direction. 🌊" },
    { emoji: "📏", title: "Massive Quads!", text: "Your legs must have their own zip code with the amount of space they take up. 🦵" },
    { emoji: "🛥️", title: "Outboard Motor!", text: "Is that an outboard motor I hear, or just you crushing another interval? 💪" },
    { emoji: "🚨", title: "Speed Trap!", text: "The local speed traps are flashing every time you take a stroke. 📸" },
    { emoji: "⚛️", title: "Physics Breaker!", text: "You didn't just break a sweat; you broke the laws of physics today. 🤯" },
    { emoji: "🦖", title: "Stegosaurus Curve!", text: "That force curve must look like the back of a stegosaurus. Peak power! 🔥" },
    { emoji: "🚓", title: "Speeding Ticket!", text: "If they handed out speeding tickets on the water, you'd be bankrupt. 💨" }
];

function didIDoGreat() {
    const btn = document.getElementById('great-btn');
    const result = document.getElementById('great-result');
    const emojiEl = document.getElementById('great-emoji');
    const titleEl = document.getElementById('great-title');
    const textEl = document.getElementById('great-text');

    if (emojiEl && titleEl && textEl) {
        const c = COMPLIMENTS[Math.floor(Math.random() * COMPLIMENTS.length)];
        emojiEl.textContent = c.emoji;
        titleEl.textContent = c.title;
        textEl.textContent = c.text;
    }

    btn.classList.add('hidden');
    result.classList.remove('hidden');
}
