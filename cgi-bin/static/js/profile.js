(() => {
  const API_ME = 'api/users/me';
  const form = document.getElementById('user-form');
  const loadingEl = document.getElementById('loading');
  const profilePicEl = document.getElementById('profile-pic');
  const messageArea = document.getElementById('message-area');

  // Inputs
  const inputs = {
    display_name: document.getElementById('display_name'),
    profile_pic: document.getElementById('profile_pic'), // note: element id same as img, but we access input by name below
    world_builder_name: document.getElementById('world_builder_name'),
    dnd_beyond_name: document.getElementById('dnd_beyond_name'),
    dnd_beyond_campaign: document.getElementById('dnd_beyond_campaign'),
    privilege_level: document.getElementById('privilege_level'),
  };

  // The profile_pic input is a text input (id "profile_pic") — but we also have an <img> with same id.
  // To avoid conflict, select the text input by name:
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
      // fade-out after 4s
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

    // show image (fallback)
    profilePicEl.src = user.profile_pic || 'https://www.gravatar.com/avatar/?d=mp&s=128';
    profilePicEl.alt = (user.display_name || 'Profile') + ' picture';

    // fill inputs
    document.getElementById('display_name').value = user.display_name ?? '';
    profilePicInput.value = user.profile_pic ?? '';
    document.getElementById('world_builder_name').value = user.world_builder_name ?? '';
    document.getElementById('dnd_beyond_name').value = user.dnd_beyond_name ?? '';
    document.getElementById('dnd_beyond_campaign').value = user.dnd_beyond_campaign ?? '';
    document.getElementById('privilege_level').value = user.privilege_level ?? '';

    loadingEl.style.display = 'none';
    form.style.display = 'block';
    setFormEnabled(false);
  }

  async function loadUser() {
    loadingEl.textContent = 'Loading…';
    try {
      const res = await fetch(API_ME, { credentials: 'same-origin' });
      if (!res.ok) {
        if (res.status === 401) {
          loadingEl.textContent = 'Not logged in.';
          return;
        }
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

  function revertChanges() {
    if (!originalData) return;
    populateForm(originalData);
    showMessage('Changes discarded', 'ok');
    setFormEnabled(false);
  }

  function readFormData() {
    return {
      // include all fields expected by the API response example
      id: currentUser.id, // keep id (server may ignore)
      display_name: document.getElementById('display_name').value.trim(),
      world_builder_name: document.getElementById('world_builder_name').value.trim(),
      dnd_beyond_name: document.getElementById('dnd_beyond_name').value.trim(),
      dnd_beyond_campaign: Number(document.getElementById('dnd_beyond_campaign').value || 0),
      privilege_level: Number(document.getElementById('privilege_level').value || 0),
      profile_pic: profilePicInput.value.trim()
    };
  }

  async function saveChanges() {
    if (saving) return;
    if (!currentUser) return showMessage('No user loaded', 'err');

    const payload = readFormData();

    // minimal validation
    if (!payload.display_name) return showMessage('Display name cannot be empty', 'err');

    saving = true;
    saveBtn.textContent = 'Saving…';
    saveBtn.disabled = true;

    const url = `api/users/${encodeURIComponent(currentUser.id)}`;
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
        showMessage('Saved successfully', 'ok');
      } else if (res.status === 400) {
        const errBody = await res.json().catch(() => null);
        showMessage('Validation error: ' + (errBody?.message || res.statusText), 'err');
      } else if (res.status === 401) {
        showMessage('Unauthorized: please log in', 'err');
      } else {
        showMessage('Save failed: ' + res.status, 'err');
      }
    } catch (err) {
      console.error(err);
      showMessage('Network error while saving', 'err');
    } finally {
      saving = false;
      saveBtn.textContent = 'Save';
      saveBtn.disabled = false;
      setFormEnabled(false);
    }
  }

  // update preview image live when profile URL changes
  function wireImagePreview() {
    profilePicInput.addEventListener('input', () => {
      const url = profilePicInput.value.trim();
      profilePicEl.src = url || 'https://www.gravatar.com/avatar/?d=mp&s=128';
    });
  }

  // wire buttons
  editBtn.addEventListener('click', () => setFormEnabled(true));
  cancelBtn.addEventListener('click', revertChanges);
  saveBtn.addEventListener('click', saveChanges);

  // initial run
  wireImagePreview();
  loadUser();
})();
