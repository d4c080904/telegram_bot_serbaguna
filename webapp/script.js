const tg = window.Telegram.WebApp;
tg.expand(); tg.setHeaderColor('#0b0f19'); tg.setBackgroundColor('#0b0f19');
const initData = tg.initData;
const headers = { 'X-Telegram-Init-Data': initData };
let cChart, wChart;

// ===== FITUR DRAG & SCROLL UNTUK LAPTOP =====
document.querySelectorAll('.sub-tabs').forEach(slider => {
    let isDown = false;
    let startX;
    let scrollLeft;

    slider.addEventListener('mousedown', (e) => {
        isDown = true;
        slider.classList.add('active');
        startX = e.pageX - slider.offsetLeft;
        scrollLeft = slider.scrollLeft;
    });
    slider.addEventListener('mouseleave', () => {
        isDown = false;
        slider.classList.remove('active');
    });
    slider.addEventListener('mouseup', () => {
        isDown = false;
        slider.classList.remove('active');
    });
    slider.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - slider.offsetLeft;
        const walk = (x - startX) * 2;
        slider.scrollLeft = scrollLeft - walk;
    });
    slider.addEventListener('wheel', (e) => {
        if (e.deltaY !== 0) {
            e.preventDefault();
            slider.scrollLeft += e.deltaY;
        }
    }, { passive: false });
});

function switchTab(tabName, btn) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('page-' + tabName).classList.add('active');
    if(btn && btn.classList.contains('nav-btn')) btn.classList.add('active');
    
    const wrapper = document.getElementById('chatInputWrapper');
    wrapper.style.display = (tabName === 'chat') ? 'flex' : 'none';
    
    const header = document.getElementById('globalHeader');
    header.style.display = (tabName === 'profile' || tabName === 'help') ? 'none' : 'flex';
    document.getElementById('app-container').style.paddingTop = (tabName === 'profile' || tabName === 'help') ? '20px' : '75px';

    if (tabName === 'history') loadHistory();
    if (tabName === 'dashboard') refreshData(); 
    if (tabName === 'gym') loadStats();
    if (tabName === 'profile') loadProfile();
    if (tabName === 'chat') loadChatHistory();
}

function switchSubTab(parent, sub, btn) {
    document.querySelectorAll(`#page-${parent} .sub-tab-btn`).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    if(parent === 'nutrisi') {
        document.getElementById('sub-nutrisi-food').style.display = (sub === 'food') ? 'block' : 'none';
        document.getElementById('sub-nutrisi-water').style.display = (sub === 'water') ? 'block' : 'none';
        document.getElementById('sub-nutrisi-meal').style.display = (sub === 'meal') ? 'block' : 'none';
    } else if (parent === 'gym') {
        document.getElementById('sub-gym-stats').style.display = (sub === 'stats') ? 'block' : 'none';
        document.getElementById('sub-gym-program').style.display = (sub === 'program') ? 'block' : 'none';
        document.getElementById('sub-gym-log').style.display = (sub === 'log') ? 'block' : 'none';
        document.getElementById('sub-gym-scan').style.display = (sub === 'scan') ? 'block' : 'none';
    }
}

async function refreshData() {
    try {
        const res = await fetch('/api/chart_data', { headers });
        if (!res.ok) throw new Error("Gagal load data");
        const data = await res.json();
        
        if(data.daily && data.daily.length > 0) {
            const today = data.daily[data.daily.length - 1];
            document.getElementById('dashWaterVal').innerText = today.total_air;
            document.getElementById('dashMasuk').innerText = today.total_kalori_masuk;
            document.getElementById('dashBakar').innerText = today.total_kalori_keluar;
            
            let target = 2500;
            document.getElementById('dashBatas').innerText = target;
            document.getElementById('dashSisa').innerText = target - (today.total_kalori_masuk - today.total_kalori_keluar);
        }
        
        // UPDATE WIDGET API (STREAK)
        if (data.streak !== undefined) {
            document.getElementById('dashStreak').innerText = data.streak;
        }
        
        renderCharts(data);
    } catch (err) { console.error(err); }
}

function renderCharts(data) {
    if (cChart) cChart.destroy(); if (wChart) wChart.destroy();
    cChart = new Chart(document.getElementById('calorieChart'), {
        type: 'bar', data: { labels: data.daily.map(i => i.tanggal), datasets: [{ label: 'Masuk', data: data.daily.map(i => i.total_kalori_masuk), backgroundColor: '#3b82f6' }, { label: 'Bakar', data: data.daily.map(i => i.total_kalori_keluar), backgroundColor: '#ef4444' }] },
        options: { responsive: true, maintainAspectRatio: false }
    });
    wChart = new Chart(document.getElementById('weightChart'), {
        type: 'line', data: { labels: data.weight.map(i => i.tanggal), datasets: [{ label: 'Berat', data: data.weight.map(i => i.berat), borderColor: '#10b981', fill: true, tension: 0.4 }] },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

async function loadStats() {
    const res = await fetch('/api/get_stats', { headers });
    const data = await res.json();
    document.getElementById('statMakan').innerText = data.stats.makanan;
    document.getElementById('statAir').innerText = data.stats.air;
    document.getElementById('statGym').innerText = data.stats.gym;
}

async function loadProfile() {
    try {
        const res = await fetch('/api/profile', { headers });
        const data = await res.json();
        document.getElementById('headerName').innerText = data.nama;
        document.getElementById('headerBmi').innerText = `BMI: ${data.bmi}`;
        document.getElementById('headerStats').innerText = `${data.tinggi} cm | ${data.berat} kg`;
        document.getElementById('profBerat').value = data.berat;
        document.getElementById('profTinggi').value = data.tinggi;
        document.getElementById('profTarget').value = data.target;
    } catch(e) {}
}

document.getElementById('foodForm').onsubmit = async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btnFood'); btn.innerText = "⏳ Proses...";
    const fd = new FormData();
    if(document.getElementById('foodImage').files.length) fd.append("food_image", document.getElementById('foodImage').files[0]);
    if(document.getElementById('foodText').value.trim()) fd.append("food_text", document.getElementById('foodText').value);
    
    const res = await fetch('/api/log_food', { method: 'POST', headers, body: fd });
    const r = document.getElementById('nutrisiResult'); r.style.display = 'block';
    if(res.ok) { const d = await res.json(); r.innerHTML = `✅ <b>Tercatat:</b><br>🍽️ ${d.data.nama_makanan}<br>🔥 ${d.data.kalori} kcal`; refreshData(); }
    else r.innerText = "❌ Gagal catat makanan.";
    btn.innerText = "🚀 Catat Makanan";
};

document.getElementById('barcodeForm').onsubmit = async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btnBarcode'); btn.innerText = "⏳ Scan...";
    const fd = new FormData(); fd.append("barcode_image", document.getElementById('barcodeImage').files[0]);
    
    const res = await fetch('/api/log_barcode', { method: 'POST', headers, body: fd });
    const r = document.getElementById('nutrisiResult'); r.style.display = 'block';
    if(res.ok) { const d = await res.json(); r.innerHTML = `✅ <b>Barcode Terdeteksi:</b><br>🛒 ${d.data.nama}<br>🔥 ${d.data.kalori} kcal`; refreshData(); }
    else { const err = await res.json(); r.innerText = `❌ ${err.detail}`; }
    btn.innerText = "📸 Scan Barcode";
};

document.getElementById('weightForm').onsubmit = async (e) => {
    e.preventDefault();
    const res = await fetch('/api/log_weight', { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ berat: document.getElementById('weightInput').value }) });
    if (res.ok) {
        document.getElementById('weightInput').value = ""; loadProfile(); refreshData();
    } else {
        const err = await res.json().catch(() => ({}));
        alert(`Gagal simpan berat: ${err.detail || 'coba lagi'}`);
    }
};

document.getElementById('gymProfileForm').onsubmit = async (e) => {
    e.preventDefault();
    const data = { target: document.getElementById('gymTarget').value, level: document.getElementById('gymLevel').value, alat: document.getElementById('gymAlat').value };
    await fetch('/api/gym_profile', { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    alert("Program Gym disimpan!");
};

document.getElementById('workoutForm').onsubmit = async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btnWorkout'); btn.innerText = "⏳ Mikir...";
    const res = await fetch('/api/log_workout', { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ teks: document.getElementById('workoutText').value }) });
    const r = document.getElementById('workoutResult'); r.style.display = 'block';
    if(res.ok) { const d = await res.json(); r.innerHTML = `✅ <b>${d.data.olahraga}</b><br>⏳ ${d.data.durasi} mnt | 🔥 ${d.data.kalori_terbakar} kcal`; refreshData(); }
    else r.innerText = "❌ Gagal menganalisis.";
    btn.innerText = "🔥 Simpan Latihan";
};

document.getElementById('equipForm').onsubmit = async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btnEquip'); btn.innerText = "⏳ Menganalisis...";
    const fd = new FormData(); fd.append("equipment_image", document.getElementById('equipImage').files[0]);
    const res = await fetch('/api/scan_equipment', { method: 'POST', headers, body: fd });
    const r = document.getElementById('equipResult'); r.style.display = 'block';
    if(res.ok) { const d = await res.json(); r.innerText = d.data; }
    else r.innerText = "❌ Gagal mengenali alat.";
    btn.innerText = "📸 Analisis Alat";
};

document.getElementById('profileForm').onsubmit = async (e) => {
    e.preventDefault();
    const res = await fetch('/api/profile', { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ berat: document.getElementById('profBerat').value, tinggi: document.getElementById('profTinggi').value, target: document.getElementById('profTarget').value }) });
    if (res.ok) {
        alert("Profil diupdate!"); loadProfile();
    } else {
        const err = await res.json().catch(() => ({}));
        alert(`Gagal update profil: ${err.detail || 'coba lagi'}`);
    }
};

async function logWater(ml) {
    await fetch('/api/log_water', { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ ml }) });
    refreshData();
}

async function generateMeal() {
    const btn = document.getElementById('btnMeal'); btn.innerText = "⏳ AI Mikir...";
    const res = await fetch('/api/meal_planner', { headers });
    const r = document.getElementById('mealResult'); r.style.display = 'block';
    if(res.ok) { const d = await res.json(); r.innerText = d.data; }
    else r.innerText = "❌ Gagal generate resep.";
    btn.innerText = "✨ Generate Resep";
}

async function exportPDF() {
    tg.showPopup({ title: "Laporan PDF", message: "Bot akan mengirim PDF ke chat Telegram lu. Lanjutkan?", buttons: [{id: "ok", type: "default", text: "Kirim"}] }, async (id) => {
        if(id === "ok") {
            tg.showAlert("Sedang membuat PDF...");
            await fetch('/api/export_pdf', { method: 'POST', headers });
        }
    });
}

async function loadHistory() {
    const list = document.getElementById('historyList');
    list.innerHTML = '<p style="text-align:center;color:var(--text-muted);font-size:13px;">Memuat timeline...</p>';
    try {
        const res = await fetch('/api/unified_history', { headers });
        const data = await res.json();
        list.innerHTML = "";
        if (!data.history || data.history.length === 0) {
            list.innerHTML = '<p style="text-align:center;color:var(--text-muted);font-size:13px;">Belum ada aktivitas hari ini.</p>';
            return;
        }
        data.history.forEach(item => {
            let icon = "📝";
            let subtext = "";
            if (item.type === 'food') {
                icon = "🍽️";
                subtext = `${item.value} kcal`;
            } else if (item.type === 'water') {
                icon = "💧";
                subtext = `+${item.value} ml`;
            } else if (item.type === 'weight') {
                icon = "⚖️";
                subtext = `${item.value} kg`;
            } else if (item.type === 'workout') {
                icon = "🏋️";
                subtext = `${item.value} kcal` + (item.durasi ? ` • ${item.durasi} mnt` : "");
            }
            list.innerHTML += `<div class="history-item">
                <div>${icon} <b>${item.title}</b><br><small>${subtext} • ${item.waktu || '--:--'}</small></div>
                <button class="btn-delete" onclick="deleteLog('${item.type}', ${item.id})">🗑️</button>
            </div>`;
        });
    } catch (err) {
        list.innerHTML = '<p style="text-align:center;color:var(--accent-red);font-size:13px;">Gagal memuat timeline.</p>';
    }
}

async function deleteLog(type, id) {
    const label = { food: "makanan", water: "air minum", weight: "berat", workout: "latihan" }[type] || type;
    if (!confirm(`Hapus catatan ${label} ini?\nData bakal ilang dari database, history, dan grafik.`)) return;
    try {
        const res = await fetch(`/api/delete_log/${type}/${id}`, { method: 'DELETE', headers });
        if (res.ok) {
            if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
            loadHistory(); refreshData(); loadStats();
        } else {
            const err = await res.json().catch(() => ({}));
            alert(`Gagal hapus: ${err.detail || 'unknown error'}`);
        }
    } catch (err) {
        alert("Koneksi error saat hapus.");
    }
}

async function loadChatHistory() {
    const res = await fetch('/api/chat/history', { headers });
    const data = await res.json();
    const c = document.getElementById('chatContainer'); c.innerHTML = "";
    data.history.forEach(m => c.innerHTML += `<div class="chat-bubble ${m.role}">${marked.parse(m.content)}</div>`);
    c.scrollTop = c.scrollHeight;
}
async function sendChatMessage() {
    const input = document.getElementById('chatInput'); const txt = input.value;
    if(!txt) return;
    const c = document.getElementById('chatContainer');
    c.innerHTML += `<div class="chat-bubble user">${txt}</div>`; input.value = "";
    c.scrollTop = c.scrollHeight;
    const res = await fetch('/api/chat/send', { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ pesan: txt }) });
    const d = await res.json();
    c.innerHTML += `<div class="chat-bubble assistant">${marked.parse(d.response)}</div>`;
    c.scrollTop = c.scrollHeight;
}
async function clearChat() {
    if(!confirm("Hapus riwayat chat?")) return;
    await fetch('/api/chat/clear', { method: 'DELETE', headers }); loadChatHistory();
}

if (!initData) {
    document.getElementById('loading-screen').style.display = 'none';
    alert("Buka lewat Telegram ya bro!");
} else {
    loadProfile(); refreshData();
    document.getElementById('loading-screen').style.display = 'none';
    document.getElementById('app-container').style.display = 'block';
}