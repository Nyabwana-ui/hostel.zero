let currentUser = null;
let dashboardData = null;
let activeCategory = 'All';

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'Something went wrong.');
  return data;
}

function showToast(message) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 2600);
}

async function login(username, password) {
  try {
    const data = await api('/api/login', { method: 'POST', body: JSON.stringify({ username, password }) });
    currentUser = data.user;
    await showApp();
  } catch (error) {
    $('#loginError').textContent = error.message;
  }
}

$('#loginForm').addEventListener('submit', (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  login(form.get('username'), form.get('password'));
});

$$('[data-login]').forEach((button) => button.addEventListener('click', () => {
  const [username, password] = button.dataset.login.split(':');
  login(username, password);
}));

$('#logoutButton').addEventListener('click', async () => {
  await api('/api/logout', { method: 'POST', body: '{}' });
  currentUser = null;
  dashboardData = null;
  $('#loginForm').reset();
  $('#loginError').textContent = '';
  $('#appView').hidden = true;
  $('#loginView').hidden = false;
});

async function showApp() {
  $('#loginView').hidden = true;
  $('#appView').hidden = false;
  $('#profileName').textContent = currentUser.name;
  $('#profileRole').textContent = currentUser.role;
  $('#profileInitial').textContent = currentUser.name.charAt(0).toUpperCase();
  $('#membersNav').hidden = !currentUser.isAdmin;
  $('#activityNav').hidden = !currentUser.isAdmin;
  await refreshDashboard();
}

function iconFor(category) {
  return ({ Electronic: '⌁', Appliance: '♨', Book: '▤', Household: '◇' })[category] || '◇';
}

function statusClass(status) {
  return status.toLowerCase().replaceAll(' ', '-');
}

function itemCard(item) {
  const canRequest = !currentUser.isAdmin && item.available && item.ownerId !== currentUser.id;
  const canDelete = !currentUser.isAdmin && item.ownerId === currentUser.id && item.available;
  return `<article class="item-card">
    <div class="item-card-top"><div class="item-icon">${iconFor(item.category)}</div><span class="status ${statusClass(item.status)}">${item.status}</span></div>
    <h3>${escapeHtml(item.name)}</h3>
    <p>${escapeHtml(item.description || 'Shared by a hostel member')}</p>
    <div class="item-meta"><span>${escapeHtml(item.category)} · ${escapeHtml(item.owner)}</span><div class="item-actions">${canRequest ? `<button class="secondary-button" data-request-item="${item.id}">Request</button>` : ''}${canDelete ? `<button class="danger-button" data-delete-item="${item.id}">Delete</button>` : '<span>4-day loan</span>'}</div></div>
  </article>`;
}

function escapeHtml(value) {
  const element = document.createElement('div');
  element.textContent = String(value ?? '');
  return element.innerHTML;
}

function renderStats() {
  const cards = [
    ['Shared items', dashboardData.stats.items],
    ['Available now', dashboardData.stats.available],
    ['On loan', dashboardData.stats.borrowed],
    ['Overdue', dashboardData.stats.overdue],
  ];
  $('#stats').innerHTML = cards.map(([label, value]) => `<article class="stat-card"><span>${label}</span><strong>${value}</strong></article>`).join('');
}

function renderCatalog() {
  const search = $('#itemSearch').value.toLowerCase();
  const items = dashboardData.items.filter((item) => {
    const matchesSearch = `${item.name} ${item.category} ${item.owner}`.toLowerCase().includes(search);
    const matchesCategory = activeCategory === 'All' || (activeCategory === 'Available' && item.available);
    return matchesSearch && matchesCategory;
  });
  $('#catalogItems').innerHTML = items.length ? items.map(itemCard).join('') : '<p>No items match this filter.</p>';
  $('#featuredItems').innerHTML = dashboardData.availableItems.slice(0, 6).map(itemCard).join('') || '<p>No items are available right now.</p>';
}

function requestActions(request) {
  if (!currentUser.isAdmin && request.ownerName === currentUser.name && request.status === 'Pending') {
    return `<button class="accept" data-approve-request="${request.id}">Approve</button><button data-reject-request="${request.id}">Reject</button>`;
  }
  if (!currentUser.isAdmin && request.borrowerName === currentUser.name && request.status === 'Approved') {
    return `<button class="accept" data-collect-request="${request.id}">Collect</button>`;
  }
  if (!currentUser.isAdmin && request.ownerName === currentUser.name && ['Borrowed', 'Overdue'].includes(request.status)) {
    return `<button class="accept" data-return-request="${request.id}">Confirm return</button>`;
  }
  return '';
}

function renderRequests() {
  const rows = dashboardData.requests;
  $('#requestList').innerHTML = rows.length ? rows.map((request) => `<article class="request-row">
    <div><strong>${escapeHtml(request.itemName)}</strong><span>${escapeHtml(request.borrowerName)} → ${escapeHtml(request.ownerName)}</span></div>
    <div><strong>${escapeHtml(request.status)}</strong><span>Status</span></div>
    <div><strong>${request.dueDate ? escapeHtml(request.dueDate) : 'Not set'}</strong><span>Due date</span></div>
    <div><strong>${request.penalty ? `${request.penalty.toLocaleString()} UGX` : '0 UGX'}</strong><span>${request.daysOverdue} days overdue</span></div>
    <div class="request-actions">${requestActions(request)}</div>
  </article>`).join('') : '<p>No borrowing activity yet.</p>';
}

function renderMembers() {
  $('#memberRows').innerHTML = dashboardData.members.map((member) => `<tr><td><strong>${escapeHtml(member.name)}</strong></td><td>${escapeHtml(member.username)}</td><td>${escapeHtml(member.room)}</td><td>${escapeHtml(member.phone)}</td><td>${member.items}</td></tr>`).join('');
}

function renderMemberActivity() {
  $('#activityGrid').innerHTML = dashboardData.memberActivity.map((member) => `<article class="activity-member">
    <div class="activity-member-head"><div><strong>${escapeHtml(member.name)}</strong><span>@${escapeHtml(member.username)} · Room ${escapeHtml(member.room)}</span></div><span class="status">${member.overdueCount} overdue</span></div>
    <div class="activity-counts"><div><strong>${member.requestsCount}</strong><span>Requests made</span></div><div><strong>${member.lendingCount}</strong><span>Requests received</span></div><div><strong>${member.itemsListed}</strong><span>Items listed</span></div></div>
    <div class="activity-feed">${member.activity.length ? member.activity.map((activity) => `<div><strong>${escapeHtml(activity.itemName)}</strong><span>${escapeHtml(activity.status)}</span><small>${activity.ownerName === member.name ? `Lending to ${escapeHtml(activity.borrowerName)}` : `Borrowed from ${escapeHtml(activity.ownerName)}`}</small></div>`).join('') : '<p>No activity recorded.</p>'}</div>
  </article>`).join('') || '<p>No member activity yet.</p>';
}

function renderProfileAndHistory() {
  const profile = dashboardData.profile;
  $('#profileAvatar').textContent = profile.name.charAt(0).toUpperCase();
  $('#profileCardName').textContent = profile.name;
  $('#profileCardRole').textContent = profile.role;
  const details = [
    ['Username', profile.username],
    ['Role', profile.role],
    ['Room', profile.room || 'Not applicable'],
    ['Phone', profile.phone || 'Not provided'],
    ['Items listed', profile.itemsListed],
  ];
  $('#profileDetails').innerHTML = details.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('');
  $('#editProfileButton').hidden = false;
  $('#historyList').innerHTML = dashboardData.history.length ? dashboardData.history.map((request) => `<article class="request-row history-row"><div><strong>${escapeHtml(request.itemName)}</strong><span>${escapeHtml(request.ownerName)}</span></div><div><strong>${escapeHtml(request.status)}</strong><span>Status</span></div><div><strong>${request.borrowDate || '-'}</strong><span>Borrowed</span></div><div><strong>${request.returnDate || '-'}</strong><span>Returned</span></div><div><strong>${request.penalty} UGX</strong><span>Penalty</span></div></article>`).join('') : '<p>Your borrowing history is empty.</p>';
}

async function refreshDashboard() {
  dashboardData = await api('/api/dashboard');
  renderStats();
  renderCatalog();
  renderRequests();
  renderMembers();
  renderMemberActivity();
  renderProfileAndHistory();
}

$$('.nav-button[data-view]').forEach((button) => button.addEventListener('click', () => {
  $$('.nav-button[data-view]').forEach((item) => item.classList.remove('active'));
  button.classList.add('active');
  $$('.view').forEach((view) => view.classList.remove('active'));
  $(`[data-view-panel="${button.dataset.view}"]`).classList.add('active');
  $('#pageTitle').textContent = button.dataset.view[0].toUpperCase() + button.dataset.view.slice(1);
}));

$$('[data-jump]').forEach((button) => button.addEventListener('click', () => $(`[data-view="${button.dataset.jump}"]`).click()));
$('#itemSearch').addEventListener('input', renderCatalog);
$('#categoryFilters').addEventListener('click', (event) => {
  if (!event.target.dataset.category) return;
  activeCategory = event.target.dataset.category;
  $$('#categoryFilters button').forEach((button) => button.classList.toggle('active', button === event.target));
  renderCatalog();
});

document.addEventListener('click', async (event) => {
  const requestButton = event.target.closest('[data-request-item]');
  if (requestButton) {
    try { await api('/api/requests', { method: 'POST', body: JSON.stringify({ itemId: Number(requestButton.dataset.requestItem) }) }); showToast('Borrow request sent.'); await refreshDashboard(); }
    catch (error) { showToast(error.message); }
  }
  const deleteButton = event.target.closest('[data-delete-item]');
  if (deleteButton && window.confirm('Delete this item from your catalog?')) {
    try {
      await api(`/api/items/${deleteButton.dataset.deleteItem}`, { method: 'DELETE', body: '{}' });
      showToast('Item deleted.');
      await refreshDashboard();
    } catch (error) {
      showToast(error.message);
    }
  }
  const approveButton = event.target.closest('[data-approve-request]');
  if (approveButton) openApproveModal(Number(approveButton.dataset.approveRequest));
  const rejectButton = event.target.closest('[data-reject-request]');
  if (rejectButton) {
    await performRequestAction(rejectButton.dataset.rejectRequest, 'reject');
  }
  const collectButton = event.target.closest('[data-collect-request]');
  if (collectButton) {
    await performRequestAction(collectButton.dataset.collectRequest, 'collect');
  }
  const returnButton = event.target.closest('[data-return-request]');
  if (returnButton) {
    await performRequestAction(returnButton.dataset.returnRequest, 'return');
  }
});

async function performRequestAction(requestId, action) {
  try {
    await api(`/api/requests/${requestId}/${action}`, { method: 'POST', body: '{}' });
    showToast('Request updated.');
    await refreshDashboard();
  } catch (error) {
    showToast(error.message);
  }
}

function openModal(title, body) {
  $('#modalTitle').textContent = title;
  $('#modalForm').innerHTML = body + '<button class="primary-button" type="submit">Save changes</button>';
  $('#modalBackdrop').hidden = false;
}
$('#modalClose').addEventListener('click', () => $('#modalBackdrop').hidden = true);
$('#modalBackdrop').addEventListener('click', (event) => { if (event.target === event.currentTarget) event.currentTarget.hidden = true; });

$('#addItemButton').addEventListener('click', () => {
  openModal('List an item', `<div class="modal-grid"><label>Name<input name="name" required></label><label>Category<select name="category"><option>Electronic</option><option>Appliance</option><option>Book</option><option>Household</option></select></label></div><label>Description<input name="description"></label><label>Brand / watts / author<input name="detail" placeholder="Optional category detail"></label>`);
  $('#modalForm').onsubmit = async (event) => {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try { await api('/api/items', { method: 'POST', body: JSON.stringify(Object.fromEntries(form)) }); $('#modalBackdrop').hidden = true; showToast('Item listed.'); await refreshDashboard(); } catch (error) { showToast(error.message); }
  };
});

$('#editProfileButton').addEventListener('click', () => {
  const profile = dashboardData.profile;
  const memberFields = currentUser.isAdmin ? '' : `<div class="modal-grid"><label>Room<input name="room" required value="${escapeHtml(profile.room || '')}"></label><label>Phone<input name="phone" pattern="[0-9]{10}" required value="${escapeHtml(profile.phone || '')}"></label></div>`;
  openModal('Edit profile', `<label>Full name<input name="name" required value="${escapeHtml(profile.name)}"></label><label>Username<input name="username" required value="${escapeHtml(profile.username)}"></label>${memberFields}<label>New password <small>(leave blank to keep current)</small><input name="password" type="password" minlength="4" autocomplete="new-password"></label>`);
  $('#modalForm').onsubmit = async (event) => {
    event.preventDefault();
    const form = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await api('/api/profile', { method: 'PUT', body: JSON.stringify(form) });
      $('#modalBackdrop').hidden = true;
      currentUser.name = form.name;
      currentUser.username = form.username;
      $('#profileName').textContent = form.name;
      $('#profileInitial').textContent = form.name.charAt(0).toUpperCase();
      showToast('Profile updated.');
      await refreshDashboard();
    } catch (error) {
      showToast(error.message);
    }
  };
});

$('#addMemberButton').addEventListener('click', () => {
  openModal('Register member', `<label>Full name<input name="name" required></label><div class="modal-grid"><label>Username<input name="username" required></label><label>Password<input name="password" minlength="4" required></label><label>Room<input name="room" required></label><label>Phone<input name="phone" pattern="[0-9]{10}" required placeholder="10 digits"></label></div>`);
  $('#modalForm').onsubmit = async (event) => {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try { await api('/api/members', { method: 'POST', body: JSON.stringify(Object.fromEntries(form)) }); $('#modalBackdrop').hidden = true; showToast('Member registered.'); await refreshDashboard(); } catch (error) { showToast(error.message); }
  };
});

function openApproveModal(requestId) {
  const request = dashboardData.requests.find((item) => item.id === requestId);
  openModal(`Approve ${request.itemName}`, '<label>Loan period (days)<input name="days" type="number" min="4" max="4" value="4" readonly required></label>');
  $('#modalForm').onsubmit = async (event) => {
    event.preventDefault(); const days = new FormData(event.currentTarget).get('days');
    try { await api(`/api/requests/${requestId}/approve`, { method: 'POST', body: JSON.stringify({ days }) }); $('#modalBackdrop').hidden = true; showToast('Request approved.'); await refreshDashboard(); } catch (error) { showToast(error.message); }
  };
}

async function restoreSession() {
  try { const data = await api('/api/session'); if (data.user) { currentUser = data.user; await showApp(); } }
  catch (error) { console.error(error); }
}
restoreSession();
