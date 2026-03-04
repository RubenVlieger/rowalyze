/* ─── RowSplit Client-Side JavaScript ─────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
    initToggle();
    initSplitSections();
    initFormSubmit();
    initSharkModal();
});


// ─── Interval Mode Toggle ──────────────────────────────────────

function initToggle() {
    const radios = document.querySelectorAll('input[name="interval_mode"]');
    const timeFields = document.getElementById('time-fields');
    const distFields = document.getElementById('distance-fields');

    if (!radios.length || !timeFields || !distFields) return;

    radios.forEach(radio => {
        radio.addEventListener('change', () => {
            if (radio.value === 'time') {
                timeFields.classList.remove('hidden');
                distFields.classList.add('hidden');
            } else {
                timeFields.classList.add('hidden');
                distFields.classList.remove('hidden');
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


// ─── Stats Chart (Homepage) ────────────────────────────────────

function initStatsChart(data) {
    const ctx = document.getElementById('stats-chart');
    if (!ctx || !data || !data.length) return;

    // Fill in missing dates between first and last
    const filled = [];
    if (data.length > 0) {
        const start = new Date(data[0].date);
        const end = new Date(data[data.length - 1].date);
        const dateMap = {};
        data.forEach(d => dateMap[d.date] = d.count);

        for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
            const key = d.toISOString().slice(0, 10);
            filled.push({ date: key, count: dateMap[key] || 0 });
        }
    }

    // Cumulative total
    let cumulative = 0;
    const cumData = filled.map(d => {
        cumulative += d.count;
        return { x: d.date, y: cumulative };
    });

    new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Total Sessions',
                data: cumData,
                borderColor: '#3b82f6',
                backgroundColor: '#3b82f620',
                borderWidth: 2,
                pointRadius: cumData.length > 30 ? 0 : 3,
                tension: 0.3,
                fill: true,
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
                    type: 'category',
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
    const submit = document.getElementById('shark-submit');
    const bookmarklet = document.getElementById('shark-bookmarklet');

    if (!btn || !modal) return;

    // Generate the bookmarklet href
    if (bookmarklet) {
        const serverUrl = window.location.origin;
        // The bookmarklet script: runs on strava.com, fetches streams, submits via form POST
        const bmCode = `javascript:void(function(){` +
            `if(!location.href.match(/strava\\.com\\/activities\\/(\\d+)/)){alert('Open a Strava activity page first!');return;}` +
            `var id=location.href.match(/\\/activities\\/(\\d+)/)[1];` +
            `var title=document.title||'Shark Activity';` +
            `var types='time,velocity_smooth,cadence,distance,heartrate';` +
            `var overlay=document.createElement('div');` +
            `overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:99999;display:flex;align-items:center;justify-content:center;';` +
            `overlay.innerHTML='<div style=\"background:white;padding:32px;border-radius:12px;text-align:center;font-family:Inter,sans-serif;\"><div style=\"font-size:2rem;\">🦈</div><div style=\"margin-top:8px;font-size:1rem;\">Fetching streams...</div></div>';` +
            `document.body.appendChild(overlay);` +
            `fetch('/api/v3/activities/'+id+'/streams?keys='+types+'&key_by_type=true',{credentials:'include'})` +
            `.then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json()})` +
            `.then(function(data){` +
            `var form=document.createElement('form');` +
            `form.method='POST';form.action='${serverUrl}/shark/receive';` +
            `var f1=document.createElement('input');f1.type='hidden';f1.name='streams';f1.value=JSON.stringify(data);form.appendChild(f1);` +
            `var f2=document.createElement('input');f2.type='hidden';f2.name='activity_url';f2.value=location.href;form.appendChild(f2);` +
            `var f3=document.createElement('input');f3.type='hidden';f3.name='activity_name';f3.value=title;form.appendChild(f3);` +
            `document.body.appendChild(form);form.submit();` +
            `})` +
            `.catch(function(e){overlay.remove();alert('Shark failed: '+e.message+'\\n\\nMake sure you are logged into Strava and can see this activity.');})` +
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

    submit.addEventListener('click', sharkSubmit);
}

async function sharkSubmit() {
    const errorEl = document.getElementById('shark-error');
    const submitBtn = document.getElementById('shark-submit');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoading = submitBtn.querySelector('.btn-loading');

    errorEl.classList.add('hidden');
    errorEl.textContent = '';

    const url = document.getElementById('shark-url').value.trim();
    const rawData = document.getElementById('shark-data').value.trim();
    const minutes = parseInt(document.getElementById('shark-minutes').value) || 4;
    const seconds = parseInt(document.getElementById('shark-seconds').value) || 50;
    const count = parseInt(document.getElementById('shark-count').value) || 3;

    if (!rawData) {
        errorEl.textContent = 'Please paste the stream JSON data.';
        errorEl.classList.remove('hidden');
        return;
    }

    // Parse the pasted JSON
    let streams;
    try {
        const parsed = JSON.parse(rawData);

        // Handle different formats: direct arrays or nested objects
        streams = {};
        const keys = ['time', 'velocity_smooth', 'cadence', 'distance', 'heartrate'];
        for (const key of keys) {
            if (key in parsed) {
                if (Array.isArray(parsed[key])) {
                    streams[key] = parsed[key];
                } else if (parsed[key] && parsed[key].data) {
                    streams[key] = parsed[key].data;
                }
            }
        }

        // Also handle if it's a list of stream objects
        if (Array.isArray(parsed)) {
            streams = {};
            parsed.forEach(s => {
                if (s.type && s.data) {
                    streams[s.type] = s.data;
                }
            });
        }

        const required = ['time', 'velocity_smooth', 'cadence', 'distance'];
        const missing = required.filter(k => !(k in streams));
        if (missing.length) {
            throw new Error(`Missing required streams: ${missing.join(', ')}`);
        }
    } catch (e) {
        errorEl.textContent = `Failed to parse JSON: ${e.message}`;
        errorEl.classList.remove('hidden');
        return;
    }

    // Show loading
    if (btnText && btnLoading) {
        btnText.classList.add('hidden');
        btnLoading.classList.remove('hidden');
    }
    submitBtn.disabled = true;

    try {
        const resp = await fetch('/api/shark', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                streams: streams,
                params: {
                    mode: 'time',
                    duration: minutes * 60 + seconds,
                    count: count,
                    min_cadence: 24,
                },
                activity: {
                    url: url || '#',
                    name: '🦈 Shark Activity',
                },
            }),
        });

        const result = await resp.json();

        if (resp.ok && result.url) {
            window.location.href = result.url;
        } else {
            throw new Error(result.error || 'Analysis failed');
        }
    } catch (e) {
        errorEl.textContent = `Error: ${e.message}`;
        errorEl.classList.remove('hidden');
    } finally {
        if (btnText && btnLoading) {
            btnText.classList.remove('hidden');
            btnLoading.classList.add('hidden');
        }
        submitBtn.disabled = false;
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

function didIDoGreat() {
    const btn = document.getElementById('great-btn');
    const result = document.getElementById('great-result');

    btn.classList.add('hidden');
    result.classList.remove('hidden');
}
