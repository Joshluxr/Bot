const API = '/api';
let token = localStorage.getItem('cp_token');
let currentUser = null;
let pollTimer = null;
let selectedJobId = null;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const SETTING_HINTS = {
  app_name: 'Dashboard title shown in the UI',
  default_target: 'Default URL for new scan jobs',
  tools_bin: 'Path to nuclei, httpx, ffuf binaries',
  wordpress_tool_dir: 'Path to wordpress-tool scripts',
  bruter_threads: 'Concurrent threads for BRUTER.py',
  ato_spray_enabled: 'Enable ATO password spray (true/false)',
  ato_spray_limit: 'Max passwords for ATO spray',
  nuclei_severity: 'Comma-separated nuclei severity filter',
  scan_timeout_seconds: 'Max seconds per scan job',
  custom_openai_api_base: 'OpenAI-compatible API base URL',
  custom_openai_api_key: 'API key (masked when saved)',
  custom_openai_model: 'Model name for Decepticon',
  decepticon_profile: 'Attack profile: eco, balanced, aggressive',
  allowed_engagement_domains: 'Comma-separated authorized domains',
  max_parallel_jobs: 'Max concurrent subprocess jobs',
  log_retention_days: 'Days to retain job logs',
  notifications_webhook: 'Optional Slack/Discord webhook URL',
  theme_accent: 'Accent color hex for UI',
};

async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401 && !path.includes('/auth/login')) {
    logout();
    throw new Error('Session expired');
  }
  const data = res.headers.get('content-type')?.includes('json') ? await res.json() : null;
  if (!res.ok) throw new Error(data?.detail || res.statusText);
  return data;
}

function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function logout() {
  token = null;
  currentUser = null;
  localStorage.removeItem('cp_token');
  clearInterval(pollTimer);
  showLogin();
}

function showLogin() {
  $('#login-screen').classList.remove('hidden');
  $('#app-shell').classList.add('hidden');
}

function showApp() {
  $('#login-screen').classList.add('hidden');
  $('#app-shell').classList.remove('hidden');
  $('#user-name').textContent = currentUser.username;
  $('#user-role').textContent = currentUser.role;
  $('#user-avatar').textContent = currentUser.username[0].toUpperCase();
  applyAdminUI();
}

function applyAdminUI() {
  const isAdmin = currentUser?.role === 'admin';
  $$('[data-admin-only]').forEach((el) => {
    el.classList.toggle('hidden', !isAdmin);
  });
  $$('.setting-save-btn').forEach((btn) => {
    btn.disabled = !isAdmin;
  });
}

async function login(e) {
  e.preventDefault();
  const username = $('#login-user').value.trim();
  const password = $('#login-pass').value;
  const err = $('#login-error');
  err.classList.add('hidden');
  try {
    const data = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    token = data.access_token;
    currentUser = data.user;
    localStorage.setItem('cp_token', token);
    showApp();
    navigate('dashboard');
    startPolling();
  } catch (ex) {
    err.textContent = ex.message || 'Login failed';
    err.classList.remove('hidden');
  }
}

async function checkSession() {
  if (!token) return showLogin();
  try {
    currentUser = await api('/auth/me');
    showApp();
    navigate('dashboard');
    startPolling();
  } catch {
    showLogin();
  }
}

function startPolling() {
  clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    const page = document.querySelector('.page:not(.hidden)');
    if (!page) return;
    const id = page.id.replace('page-', '');
    if (id === 'dashboard' || id === 'jobs') refreshPage(id);
    if (id === 'jobs' && selectedJobId) loadJobLog(selectedJobId, true);
  }, 4000);
}

function navigate(page) {
  $$('.nav-item').forEach((n) => n.classList.toggle('active', n.dataset.page === page));
  $$('.page').forEach((p) => p.classList.add('hidden'));
  $(`#page-${page}`).classList.remove('hidden');
  refreshPage(page);
}

async function refreshPage(page) {
  try {
    if (page === 'dashboard') await loadDashboard();
    if (page === 'jobs') await loadJobs();
    if (page === 'tools') await loadTools();
    if (page === 'settings') await loadSettings();
    if (page === 'engagements') await loadEngagements();
    if (page === 'audit') await loadAudit();
  } catch (ex) {
    console.error(ex);
  }
}

async function loadDashboard() {
  const stats = await api('/stats');
  $('#stat-total').textContent = stats.total_jobs;
  $('#stat-running').textContent = stats.running;
  $('#stat-success').textContent = stats.success;
  $('#stat-failed').textContent = stats.failed;
  $('#stat-engagements').textContent = stats.engagements;
  $('#stat-queued').textContent = stats.queued;

  const tbody = $('#recent-jobs-body');
  tbody.innerHTML = (stats.recent_jobs || []).map((j) => `
    <tr>
      <td>#${j.id}</td>
      <td>${esc(j.name)}</td>
      <td><code>${esc(j.tool)}</code></td>
      <td>${statusPill(j.status)}</td>
      <td>${formatTime(j.created_at)}</td>
    </tr>
  `).join('') || '<tr><td colspan="5" class="empty-state">No jobs yet</td></tr>';

  const running = await api('/jobs/running');
  $('#running-badge').textContent = running.length;
  $('#running-badge').classList.toggle('hidden', running.length === 0);
}

async function loadJobs() {
  const jobs = await api('/jobs?limit=100');
  const tbody = $('#jobs-body');
  tbody.innerHTML = jobs.map((j) => `
    <tr data-job="${j.id}" class="${selectedJobId === j.id ? 'selected' : ''}" style="cursor:pointer">
      <td>#${j.id}</td>
      <td>${esc(j.name)}</td>
      <td><code>${esc(j.tool)}</code></td>
      <td>${esc(j.target || '—')}</td>
      <td>${statusPill(j.status)}</td>
      <td>${j.pid || '—'}</td>
      <td>${formatTime(j.created_at)}</td>
      <td>
        ${currentUser.role === 'admin' && ['running', 'queued'].includes(j.status)
          ? `<button class="btn btn-danger btn-sm" onclick="event.stopPropagation();stopJob(${j.id})">Stop</button>`
          : ''}
      </td>
    </tr>
  `).join('') || '<tr><td colspan="8"><div class="empty-state">No jobs</div></td></tr>';

  tbody.querySelectorAll('tr[data-job]').forEach((row) => {
    row.addEventListener('click', () => {
      selectedJobId = parseInt(row.dataset.job, 10);
      loadJobLog(selectedJobId);
      loadJobs();
    });
  });

  if (selectedJobId) loadJobLog(selectedJobId, true);
}

async function loadJobLog(jobId, silent = false) {
  const job = await api(`/jobs/${jobId}`);
  $('#log-title').textContent = `Job #${job.id} — ${job.name}`;
  const log = job.log_tail || '(waiting for output…)';
  const viewer = $('#job-log');
  const atBottom = viewer.scrollTop + viewer.clientHeight >= viewer.scrollHeight - 40;
  viewer.textContent = log;
  viewer.classList.toggle('empty', !job.log_tail);
  if (atBottom || !silent) viewer.scrollTop = viewer.scrollHeight;
}

async function stopJob(id) {
  if (!confirm('Stop this job?')) return;
  try {
    await api(`/jobs/${id}/stop`, { method: 'POST' });
    toast('Job stopped');
    loadJobs();
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

async function loadTools() {
  const tools = await api('/tools');
  const settings = await api('/settings');
  const defaultTarget = settings.find((s) => s.key === 'default_target')?.value || '';
  $('#tools-grid').innerHTML = tools.map((t) => `
    <div class="tool-card">
      <h4>${esc(t.name)}</h4>
      <p>${esc(t.description)}</p>
      <div class="actions">
        <button class="btn btn-primary btn-sm" data-admin-only
          onclick="openLaunchModal('${t.id}', '${esc(t.name)}')">Launch</button>
      </div>
    </div>
  `).join('');
  $('#launch-default-target').value = defaultTarget;
  applyAdminUI();
}

function openLaunchModal(toolId, toolName) {
  $('#launch-tool-id').value = toolId;
  $('#launch-modal-title').textContent = `Launch: ${toolName}`;
  $('#launch-target').value = $('#launch-default-target').value || '';
  $('#launch-modal').classList.remove('hidden');
}

function closeLaunchModal() {
  $('#launch-modal').classList.add('hidden');
}

async function submitLaunch(e) {
  e.preventDefault();
  const tool = $('#launch-tool-id').value;
  const target = $('#launch-target').value.trim();
  const name = $('#launch-name').value.trim();
  try {
    const data = await api('/jobs', {
      method: 'POST',
      body: JSON.stringify({ tool, target, params: { name: name || undefined } }),
    });
    toast(`Job #${data.job_id} queued`);
    closeLaunchModal();
    selectedJobId = data.job_id;
    navigate('jobs');
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

async function loadSettings() {
  const settings = await api('/settings');
  const grid = $('#settings-grid');
  const accent = settings.find((s) => s.key === 'theme_accent')?.value;
  if (accent) document.documentElement.style.setProperty('--accent', accent);

  grid.innerHTML = settings.map((s) => `
    <div class="setting-row" data-key="${esc(s.key)}">
      <div>
        <div class="key">${esc(s.key)}</div>
        <div class="hint">${SETTING_HINTS[s.key] || ''}</div>
      </div>
      <div>
        <input type="${s.key.includes('key') || s.key.includes('password') ? 'password' : 'text'}"
          id="setting-${esc(s.key)}" value="${esc(s.value)}"
          ${currentUser.role !== 'admin' ? 'readonly' : ''}
          placeholder="${s.masked ? 'Enter new value to update' : ''}" />
      </div>
      <div>
        <button class="btn btn-primary btn-sm setting-save-btn"
          onclick="saveSetting('${esc(s.key)}')" data-admin-only>Save</button>
      </div>
    </div>
  `).join('');

  $('#app-title').textContent = settings.find((s) => s.key === 'app_name')?.value || 'Control Panel';
  applyAdminUI();
}

async function saveSetting(key) {
  const input = $(`#setting-${key}`);
  try {
    await api(`/settings/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value: input.value }),
    });
    toast(`Saved ${key}`);
    loadSettings();
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

async function saveAllSettings() {
  const rows = $$('.setting-row');
  const updates = {};
  rows.forEach((row) => {
    const key = row.dataset.key;
    const val = $(`#setting-${key}`).value;
    if (val && val !== '••••••••') updates[key] = val;
  });
  try {
    const res = await api('/settings/bulk', { method: 'POST', body: JSON.stringify(updates) });
    toast(`Updated ${res.updated} settings`);
    loadSettings();
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

async function loadEngagements() {
  const items = await api('/engagements');
  $('#engagements-body').innerHTML = items.map((e) => `
    <tr>
      <td>${esc(e.name)}</td>
      <td><a href="${esc(e.target_url)}" target="_blank" rel="noopener">${esc(e.target_url)}</a></td>
      <td>${esc(e.notes || '—')}</td>
      <td>${statusPill(e.status || 'active')}</td>
      <td>${formatTime(e.created_at)}</td>
      <td data-admin-only>
        <button class="btn btn-danger btn-sm" onclick="deleteEngagement(${e.id})">Delete</button>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="6"><div class="empty-state">No engagements</div></td></tr>';
  applyAdminUI();
}

function openEngagementModal() {
  $('#engagement-modal').classList.remove('hidden');
}

function closeEngagementModal() {
  $('#engagement-modal').classList.add('hidden');
  $('#engagement-form').reset();
}

async function submitEngagement(e) {
  e.preventDefault();
  try {
    await api('/engagements', {
      method: 'POST',
      body: JSON.stringify({
        name: $('#eng-name').value.trim(),
        target_url: $('#eng-url').value.trim(),
        notes: $('#eng-notes').value.trim(),
      }),
    });
    toast('Engagement created');
    closeEngagementModal();
    loadEngagements();
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

async function deleteEngagement(id) {
  if (!confirm('Delete this engagement?')) return;
  try {
    await api(`/engagements/${id}`, { method: 'DELETE' });
    toast('Deleted');
    loadEngagements();
  } catch (ex) {
    toast(ex.message, 'error');
  }
}

async function loadAudit() {
  const rows = await api('/audit?limit=150');
  $('#audit-body').innerHTML = rows.map((a) => `
    <tr>
      <td>${formatTime(a.created_at)}</td>
      <td>${esc(a.username || 'system')}</td>
      <td><code>${esc(a.action)}</code></td>
      <td>${esc(a.resource || '—')}</td>
      <td>${esc(a.details || '—')}</td>
    </tr>
  `).join('') || '<tr><td colspan="5"><div class="empty-state">No audit entries</div></td></tr>';
}

function statusPill(status) {
  const s = (status || 'unknown').toLowerCase();
  return `<span class="status-pill status-${s}">${esc(s)}</span>`;
}

function formatTime(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Event wiring
document.addEventListener('DOMContentLoaded', () => {
  $('#login-form').addEventListener('submit', login);
  $('#logout-btn').addEventListener('click', logout);
  $$('.nav-item').forEach((btn) => {
    btn.addEventListener('click', () => navigate(btn.dataset.page));
  });
  $('#launch-form').addEventListener('submit', submitLaunch);
  $('#engagement-form').addEventListener('submit', submitEngagement);
  $('#save-all-settings').addEventListener('click', saveAllSettings);
  $('#new-engagement-btn').addEventListener('click', openEngagementModal);
  checkSession();
});

window.openLaunchModal = openLaunchModal;
window.closeLaunchModal = closeLaunchModal;
window.closeEngagementModal = closeEngagementModal;
window.stopJob = stopJob;
window.saveSetting = saveSetting;
window.deleteEngagement = deleteEngagement;
