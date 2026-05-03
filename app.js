// --- OVULITE STATE MANAGEMENT ---
const state = {
    currentRoute: 'dashboard',
    user: { role: 'ET Technician' },
    db: {
        recipients: [{ id: 'R-101', name: 'Daisy', status: 'Ready' }],
        embryos: [{ id: 'E-705', grade: '1', ai_score: '88%' }],
        transfers: []
    }
};

// --- ROUTING ENGINE ---
const routes = {
    dashboard: () => `
        <div class="container">
            <h1 class="title">Command Center</h1>
            <div class="grid cols-3">
                <div class="card"><div class="muted">Pending Grades</div><div class="kpi">05</div></div>
                <div class="card"><div class="muted">Pregnancy Checks</div><div class="kpi">12</div></div>
                <div class="card"><div class="muted">AI Accuracy</div><div class="kpi">94%</div></div>
            </div>
        </div>`,

    'start-et': () => `
        <div class="container">
            <div class="card">
                <h3>Start New Embryo Transfer</h3>
                <div class="stepper">
                    <div class="step active">1. Ident</div>
                    <div class="step">2. Bio</div>
                    <div class="step">3. AI</div>
                    <div class="step">4. Confirm</div>
                </div>
                <form id="etForm" class="grid gap-16">
                    <div class="field">
                        <label>Select Recipient (Digital Twin)</label>
                        <select name="recipient_id">
                            ${state.db.recipients.map(r => `<option value="${r.id}">${r.id} - ${r.name}</option>`).join('')}
                        </select>
                    </div>
                    <div class="grid cols-2">
                        <div class="field">
                            <label>CL Size (mm)</label>
                            <input type="number" name="cl_size" placeholder="22.5">
                        </div>
                        <div class="field">
                            <label>Doppler Score</label>
                            <select name="doppler">
                                <option value="1">1 - Low</option>
                                <option value="2">2 - Medium</option>
                                <option value="3">3 - High</option>
                            </select>
                        </div>
                    </div>
                    <button type="submit" class="btn primary">Run AI Prediction</button>
                </form>
            </div>
        </div>`
};

// --- RENDERER ---
function navigate(route) {
    state.currentRoute = route;
    const app = document.getElementById('app');
    const navTemplate = document.getElementById('nav-template');
    
    // Clear and Render Nav + Content
    app.innerHTML = '';
    app.appendChild(navTemplate.content.cloneNode(true));
    
    const content = document.createElement('div');
    content.innerHTML = routes[route] ? routes[route]() : `<h1>404 - Not Found</h1>`;
    app.appendChild(content);

    // Update Role Badge
    document.getElementById('roleBadge').innerText = state.user.role;
    
    // Re-attach Event Listeners
    attachListeners();
}

function attachListeners() {
    document.querySelectorAll('[data-route]').forEach(btn => {
        btn.onclick = () => navigate(btn.getAttribute('data-route'));
    });
}

// Initialize
window.onload = () => navigate('dashboard');