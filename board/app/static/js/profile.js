(() => {
  const form = document.getElementById('user-form');
  const loadingEl = document.getElementById('loading');
  const profilePicEl = document.getElementById('profile-pic');
  const messageArea = document.getElementById('message-area');
  const container = document.getElementById("profile-container");
  const userId = container.dataset.userId;  // "me" or numeric id

  const inputs = {
    display_name: document.getElementById('display_name'),
    world_builder_name: document.getElementById('world_builder_name'),
    dnd_beyond_name: document.getElementById('dnd_beyond_name'),
  };

  const profilePicInput = document.querySelector('input[name="profile_pic"]');
  const editBtn = document.getElementById('edit-btn');
  const saveBtn = document.getElementById('save-btn');
  const cancelBtn = document.getElementById('cancel-btn');

  let currentUser = null;
  let originalData = null;
  let saving = false;

  function showMessage(msg, type = 'ok') {
    messageArea.innerHTML = `<div class="message ${type === 'ok' ? 'ok' : 'err'}">${escapeHtml(msg)}</div>`;
    setTimeout(() => {
      if (messageArea.firstChild) messageArea.firstChild.style.opacity = '0.9';
    }, 4000);
  }

  function escapeHtml(s = '') {
    return String(s)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function setFormEnabled(enabled) {
    form.querySelectorAll('input').forEach(i => i.disabled = !enabled);
    saveBtn.disabled = !enabled;
    cancelBtn.disabled = !enabled;
    editBtn.disabled = enabled;
  }

  function populateForm(user) {
    if (!user) return;
    currentUser = user;
    originalData = JSON.parse(JSON.stringify(user));

    // Profile picture
    profilePicEl.src = user.profile_pic || 'https://www.gravatar.com/avatar/?d=mp&s=128';
    profilePicEl.alt = (user.display_name || 'Profile') + ' picture';

    // Editable inputs
    inputs.display_name.value = user.display_name ?? '';
    inputs.world_builder_name.value = user.world_builder_name ?? '';
    inputs.dnd_beyond_name.value = user.dnd_beyond_name ?? '';
    profilePicInput.value = user.profile_pic ?? '';

    // Display-only fields
    document.getElementById('dnd_beyond_campaign_display').textContent =
      user.dnd_beyond_campaign ?? '—';
    document.getElementById('privilege_level_display').textContent =
      user.privilege_level ?? '—';

    loadingEl.style.display = 'none';
    form.style.display = 'block';
    setFormEnabled(false);
  }

  async function loadUser() {
    loadingEl.textContent = 'Loading…';
    try {
      const url = userId === "me" ? "/api/users/me" : `/api/users/${userId}`;
      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) {
        loadingEl.textContent = `Error loading user: ${res.status}`;
        return;
      }
      const user = await res.json();
      populateForm(user);
    } catch (err) {
      loadingEl.textContent = 'Network error while loading user.';
      console.error(err);
    }
  }

  function readFormData() {
    return {
      display_name: inputs.display_name.value.trim(),
      world_builder_name: inputs.world_builder_name.value.trim(),
      dnd_beyond_name: inputs.dnd_beyond_name.value.trim(),
    };
  }

 function revertChanges() {
  if (!originalData) return;
  populateForm(originalData);
  showToast('Changes discarded', 'confirm');
  setFormEnabled(false);
}

async function saveChanges() {
  if (saving) return;
  if (!currentUser) return showToast('No user loaded', 'error');

  const payload = readFormData();
  if (!payload.display_name) return showToast('Display name cannot be empty', 'error');

  saving = true;
  saveBtn.textContent = 'Saving…';
  saveBtn.disabled = true;

  const url = `/api/users/${encodeURIComponent(currentUser.id)}`;
  try {
    const res = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const updated = await res.json();
      populateForm(updated);
      showToast('Saved successfully', 'confirm');
    } else if (res.status === 400) {
      const errBody = await res.json().catch(() => null);
      showToast('Validation error: ' + (errBody?.message || res.statusText), 'error');
    } else if (res.status === 401) {
      showToast('Unauthorized: please log in', 'error');
    } else {
      showToast('Save failed: ' + res.status, 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('Network error while saving', 'error');
  } finally {
    saving = false;
    saveBtn.textContent = 'Save';
    saveBtn.disabled = false;
    setFormEnabled(false);
  }
}

  function wireImagePreview() {
    profilePicInput.addEventListener('input', () => {
      const url = profilePicInput.value.trim();
      profilePicEl.src = url || 'https://www.gravatar.com/avatar/?d=mp&s=128';
    });
  }

  editBtn.addEventListener('click', () => setFormEnabled(true));
  cancelBtn.addEventListener('click', revertChanges);
  saveBtn.addEventListener('click', saveChanges);

  wireImagePreview();
  loadUser();
})();
