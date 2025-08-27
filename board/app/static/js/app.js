// ——— Globals & Helpers ———
var currentWeekOffset = 0;
var currentUserName = null; // track logged in user
var currentPrivilegeLevel = null; // track privilege_level
var adventureMode = "POST"
var selectedPlayerIds = []; // This will store the IDs of players that the creator selects



// ——— Initialize on Page Load ———
window.onload = async () => {
  currentWeekOffset = 0;    // reset to current week
  attachWeekNav();          // wire up your Prev/Next buttons

  const stored = localStorage.getItem('username');
  if (stored) {
    currentUserName = stored;
    updateUserUI();
  }
  else {
    await setCurrentUser();
  }
  loadAdventures();
};

// ——— Set buttons ———
document.addEventListener("DOMContentLoaded", () => {
  // Header buttons
  document.getElementById("icon-button").addEventListener("click", openHelp);
  document.getElementById("login-button").addEventListener("click", handleLoginClick);

  // Dropdown actions
  document.getElementById("edit-profile").addEventListener("click", (e) => {
    e.preventDefault();
    editProfile();
  });

  document.getElementById("make-assignments").addEventListener("click", (e) => {
    e.preventDefault();
    makeAssignments("assign");
  });

  document.getElementById("release-assignments").addEventListener("click", (e) => {
    e.preventDefault();
    makeAssignments("release");
  });

  document.getElementById("reset-assignments").addEventListener("click", (e) => {
    e.preventDefault();
    makeAssignments("reset");
  });

  document.getElementById("update-karma").addEventListener("click", (e) => {
    e.preventDefault();
    updateKarma();
  });

  document.getElementById("logout").addEventListener("click", (e) => {
    e.preventDefault();
    logout();
  });

  // Modal
  document.getElementById("close-modal").addEventListener("click", closeModal);

  // Load players
  document.getElementById("open-player-select").addEventListener("click", loadPlayersForSelect);
});


// ——— Functions ———
function handleLoginClick() {
  if (!currentUserName) {
    window.location.href = "api/login";
  } else {
    toggleDropdown();
  }
}

function openHelp()
{
  window.location.href = "help";
}

function editProfile() {
  window.location.href = "profile/me";
}

/** Returns [startOfWeek (Mon), endOfWeek (Sun)] for today + offset weeks */
function getWeekRange(offset = 0) {
  const now = new Date();
  // shift to Monday
  const day = now.getDay();
  const monday = new Date(now);
  monday.setDate(now.getDate() - (day === 0 ? 6 : day - 1) + offset * 7);
  monday.setHours(0, 0, 0, 0);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  sunday.setHours(23, 59, 59, 999);
  return [monday, sunday];
}

/** Full weeks between two dates (rounded) */
function weeksBetween(start, end) {
  return Math.round((end - start) / (7 * 24 * 60 * 60 * 1000));
}

/** Update the “Week of …” label */
function updateWeekLabel() {
  const [start, end] = getWeekRange(currentWeekOffset);
  const fmt = d => d.toLocaleDateString('default', { month: 'short', day: 'numeric' });
  document.getElementById('week-label').textContent = `Week of ${fmt(start)} – ${fmt(end)}`;
}



// Helper
const DEFAULT_AVATAR = 'https://www.gravatar.com/avatar/?d=mp&s=64';

function normalizeFromPlayersArray(player) {
  return {
    id: player.id ?? player.user_id ?? null,
    username: player.username ?? player.display_name ?? player.name ?? 'Unknown',
    karma: player.karma ?? (player.user && player.user.karma) ?? null,
    profile_pic: player.profile_pic ?? (player.user && player.user.profile_pic) ?? null,
    appeared: player.appeared ?? false
  };
}

function normalizeFromAssignmentsArray(assignment) {
  const u = assignment.user ?? {};
  return {
    id: u.id ?? assignment.id ?? null,
    username: u.display_name ?? u.username ?? 'Unknown',
    karma: u.karma ?? null,
    profile_pic: u.profile_pic ?? null,
    appeared: !!assignment.appeared
  };
}

/**
 * Build HTML string for player list.
 * Supports adventure.players[] or adventure.assignments[].
 * @param {Object} adventure
 * @param {string} currentUserName
 * @returns {string}
 */
function buildPlayerListHtml(adventure, currentUserName = '') {
  if (!adventure) return 'No players assigned yet';

  let participants = [];

  if (Array.isArray(adventure.players) && adventure.players.length > 0) {
    participants = adventure.players.map(normalizeFromPlayersArray);
  } else if (Array.isArray(adventure.assignments) && adventure.assignments.length > 0) {
    participants = adventure.assignments.map(normalizeFromAssignmentsArray);
  }

  if (!participants.length) return 'No players assigned yet';

  return participants.map(player => {
    const safeId = Util.escapeHtml(player.id ?? '');
    const safeAdvId = Util.escapeHtml(adventure.id ?? '');
    const safeName = Util.escapeHtml(player.username);
    const avatar = Util.escapeHtml(player.profile_pic || DEFAULT_AVATAR);
    const isOwn = player.username === currentUserName ? 'own-player' : '';

    return `
  <div class="draggable-player ${isOwn}"
       draggable="true"
       data-player-id="${safeId}"
       data-adventure-id="${safeAdvId}"
       title="${safeName}"
       data-click="profile">
    <img class="player-avatar" src="${avatar}" alt="${safeName}'s avatar" width="36" height="36" />
    <div class="player-meta">
      <span class="player-name">${Util.escapeHtml(Util.truncate(player.username, 16))}</span><br>
      ${player.karma != null ? `<span class="player-karma">${Util.escapeHtml(player.karma)} ✨</span>` : ''}
      ${
        player.appeared === true
          ? `<span class="player-appeared toggle-appeared" aria-label="Appeared" title="Appeared"> ✅</span>`
          : player.appeared === false
            ? `<span class="player-appeared toggle-appeared" aria-label="Not appeared" title="Not appeared"> ❌</span>`
            : '' // nothing if missing
      }
    </div>
  </div>
`;

  }).join('');
}

document.addEventListener('click', async (e) => {
  const playerEl = e.target.closest('.draggable-player');
  if (!playerEl) return;

  const user_id = playerEl.dataset.playerId;
  const adventure_id = playerEl.dataset.adventureId;

  // ✅/❌ toggler
  if (e.target.classList.contains('toggle-appeared')) {
    e.stopPropagation();

    const current = e.target.textContent.trim();
    let appearedNow;

    if (current === '✅') {
      appearedNow = false; // flip to ❌
      e.target.textContent = '❌';
    } else {
      appearedNow = true; // flip to ✅ (also covers ❌ or "no icon" case)
      e.target.textContent = '✅';
    }

    try {
      await fetch('api/player-assignments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id,
          adventure_id,
          appeared: appearedNow
        }),
      });
    } catch (err) {
      console.error('Failed to update signup:', err);
      // Rollback UI on error
      e.target.textContent = current;
    }
    return;
  }

  // 👤 Profile click (ignore checkmark)
  if (playerEl.dataset.click === 'profile') {
    window.location.href = `profile/${user_id}`;
  }
});



// ===== Modified loadAdventures (integrated) =====
async function loadAdventures() {
  updateWeekLabel();
  const [weekStart, weekEnd] = getWeekRange(currentWeekOffset);

  // Build the query string
  const params = new URLSearchParams();
  params.set('user', currentUserName);
  // always include week bounds
  params.set('week_start', weekStart.toISOString().split('T')[0]);
  params.set('week_end', weekEnd.toISOString().split('T')[0]);

  // 1) fetch data 
  const [advRes, signupRes] = await Promise.all([
    fetch(`api/adventures?${params.toString()} `),
    fetch(`api/signups?user=${currentUserName}`)
  ]);
  const adventures = await advRes.json();
  // Check if signupRes is OK before parsing
  let userSignups = [];
  if (signupRes.ok) {
    userSignups = await signupRes.json();
  } else if (signupRes.status === 401) {
    console.log('User not logged in, skipping signups');
  } else {
    console.error('Signup fetch failed:', signupRes.status);
  }

  // 2) clear grid
  const container = document.getElementById('adventure-grid');
  container.innerHTML = '';

  // 3) render everything returned (already only this week)
  adventures
    .sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
    .forEach(adventure => {
      const card = document.createElement('div');
      card.className = 'adventure-card';

      if (adventure.id === -999) {
        card.classList.add('adventure-card-wait');
      }

      const start = new Date(adventure.start_date);
      const end = new Date(adventure.end_date);
      if (weeksBetween(start, end) >= 3) {
        card.classList.add('long');
      }

      // safe title/desc handling
      const titleRaw = adventure.title ?? '';
      const descRaw = adventure.short_description ?? '';
      const title = Util.escapeHtml(titleRaw.length > 16 ? titleRaw.slice(0, 32) + '…' : titleRaw);
      const desc = Util.escapeHtml(descRaw.length > 64 ? descRaw.slice(0, 64) + '…' : descRaw);

      const signed = userSignups.find(s => s.adventure_id === adventure.id);
      const signedPriority = signed?.priority; // undefined if not signed
      const getHighlight = (prio) => (signedPriority === prio ? 'highlighted' : '');

      // use the helper to build the player list markup
      const playerListHtml = buildPlayerListHtml(adventure, currentUserName);

      card.innerHTML = `
            <h2>${title}</h2>
            <p>${desc}</p>
            <p><strong>Players:</strong>
              <div class="player-list" 
                  data-adventure-id="${Util.escapeHtml(adventure.id)}" 
                  ondrop="drop(event)" 
                  ondragover="allowDrop(event)">
                ${playerListHtml}
              </div>
            </p>
            <div >
              <button style="width: 140px;" onclick="moreDetails(${Util.escapeHtml(adventure.id)})">More Details</button>
              <div style="margin-top: 10px;">
                <button class="${getHighlight(1)}" onclick="signUp(this, ${Util.escapeHtml(adventure.id)}, 1)">🥇</button>
                <button class="${getHighlight(2)}" onclick="signUp(this, ${Util.escapeHtml(adventure.id)}, 2)">🥈</button>
                <button class="${getHighlight(3)}" onclick="signUp(this, ${Util.escapeHtml(adventure.id)}, 3)">🥉</button>
              </div>
            </div>
          `;

      container.appendChild(card);
    });


  // 4) “+” card
  const addCard = document.createElement('div');
  addCard.className = 'adventure-card add-card';
  addCard.innerHTML = `<button class="plus-btn" onclick="openModal()">+</button>`;
  container.appendChild(addCard);

  // 5) re-attach drag handlers for all generated .draggable-player elements
  container.querySelectorAll('.draggable-player').forEach(el => {
    el.addEventListener('dragstart', e => {
      // e.target might be child (img or span) so fetch closest draggable-player
      const dragEl = e.currentTarget;
      const playerId = dragEl.dataset.playerId;
      const fromAdventureId = dragEl.dataset.adventureId;

      // set both legacy keys and a json payload for flexibility
      try {
        e.dataTransfer.setData('application/json', JSON.stringify({
          playerId,
          fromAdventureId
        }));
      } catch (err) {
        // Some browsers may throw for unsupported types in certain contexts; ignore safely
      }
      e.dataTransfer.setData('playerId', playerId ?? '');
      e.dataTransfer.setData('fromAdventureId', fromAdventureId ?? '');
      e.dataTransfer.effectAllowed = 'move';

      // visual cue
      dragEl.classList.add('dragging');
    });

    el.addEventListener('dragend', (e) => {
      e.currentTarget.classList.remove('dragging');
    });
  });
}




// ——— Week Nav Buttons ———
function attachWeekNav() {
  document.getElementById('prev-week').addEventListener('click', () => {
    currentWeekOffset--;
    loadAdventures();
  });
  document.getElementById('next-week').addEventListener('click', () => {
    currentWeekOffset++;
    loadAdventures();
  });
}



function changeWeek(offset) {
  currentWeekOffset += offset;
  loadAdventures();
}


// Function to calculate next Wednesday
function getNextWednesday() {
  const today = new Date();
  const nextWednesday = new Date(today);
  nextWednesday.setDate(today.getDate() + (3 - today.getDay() + 7) % 7); // Find next Wednesday

  return nextWednesday.toISOString().split('T')[0]; // Format as YYYY-MM-DD
}

// Function to calculate the last Wednesday of the current month
function getLastWednesdayOfMonth() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();            // 0 = January, … , 11 = December

  // 1) Find the very last day of this month:
  const lastDay = new Date(year, month + 1, 0);

  // 2) Figure out how many days *past* Wednesday it is:
  //    getDay(): 0=Sun … 3=Wed … 6=Sat
  const daysPastWednesday = (lastDay.getDay() - 3 + 7) % 7;

  // 3) Subtract to land on that Wednesday:
  const lastWednesdayDate = lastDay.getDate() - daysPastWednesday;
  const lastWed = new Date(year, month, lastWednesdayDate);

  // 4) Format as YYYY-MM-DD in local time:
  const yyyy = lastWed.getFullYear();
  const mm = String(lastWed.getMonth() + 1).padStart(2, '0');
  const dd = String(lastWed.getDate()).padStart(2, '0');

  return `${yyyy}-${mm}-${dd}`;
}



// Function to initialize the form with dates
function initializeDateFields() {
  const startDateInput = document.getElementById("start-date");
  const endDateInput = document.getElementById("end-date");

  // Set next Wednesday as the start date
  startDateInput.value = getNextWednesday();

  // Set last Wednesday of the current month as the end date
  endDateInput.value = getLastWednesdayOfMonth();
}

async function moreDetails(adventure_id) {
  document.getElementById('modal').style.display = 'block';
  document.getElementById("open-player-select").style.visibility = 'hidden';
  document.getElementById("current-players-list").style.display = 'none';
  
  const params = new URLSearchParams();
  params.set('adventure_id', adventure_id);
  const res = await fetch(`api/adventures?${params.toString()}`);
  
  if (res.ok) {
    const data = await res.json();
    const adventure = data[0];
    console.log(adventure);

    // Hide save if user is not the creator
    if (currentUserName !== adventure.creator) {
      document.getElementById("save-adventure").style.visibility = 'hidden';
    }

    // Map simple fields first
    const fieldMap = {
      "title": "title",
      "description": "short_description",
      "start-date": "start_date",
      "end-date": "end_date",
      "max-players": "max_players"
    };

    Object.entries(fieldMap).forEach(([id, key]) => {
      const el = document.getElementById(id);
      if (el) {
        el.value = adventure[key];
        el.defaultValue = el.value;
        el.textContent = el.value;
      }

    });

    // Fetch and display creator display_name
    const creatorEl = document.getElementById("creator");
    if (creatorEl && adventure.user_id) {
      try {
        const userRes = await fetch(`api/users/${adventure.user_id}`);
        if (userRes.ok) {
          const userData = await userRes.json();
          creatorEl.textContent = userData.display_name || adventure.user_id;
        } else {
          creatorEl.textContent = adventure.user_id; // fallback
        }
      } catch (err) {
        console.error("Failed to fetch creator:", err);
        creatorEl.textContent = adventure.user_id; // fallback
      }
    }

    adventureMode = 'PATCH';
  } else {
    Util.showToast('Failed to load adventure details.');
  }
}


// Open the modal and load available players
async function openModal() {
  if (!currentUserName) {
    Util.showToast("Please login to create a new adventure.", "alert");
    return;
  }
  document.getElementById('modal').style.display = 'block';
  document.getElementById('creator').value = currentUserName; // set creator name
  document.getElementById("open-player-select").style.visibility='visible';
  document.getElementById("current-players-list").style.display = 'none';
  document.getElementById("save-adventure").style.visibility = 'visible';
  initializeDateFields();
  adventureMode = 'POST';
}

// Close the modal
function closeModal() {
  document.getElementById('modal').style.display = 'none';
  //initializeDateFields(); // reset date fields
}

async function signUp(btn, adventureId, priority) {
  const res = await fetch('api/signups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({adventure_id: adventureId, priority: priority})
  });

  if (res.ok) {
    loadAdventures(); // refresh to update button highlights
  } else {
    Util.showToast('Failed to sign up: Are you logged in?');
  }
}

// Load the list of available players for selection
async function loadPlayersForSelect() {
  document.getElementById("open-player-select").style.visibility='hidden';
  const select = document.getElementById('selector')
  try {
    const res = await fetch("api/users");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const users = await res.json(); 

    users.forEach(user => {
      var option = document.createElement("option");
      option.text = user.username;
      option.value = user.id;
      select.add(option);
    });

  } catch (err) {
    Util.showToast("Failed to load user list:" + err);
  }

  $('select').chosen({ width:'100%', max_shown_results: 5 });
  document.getElementById("current-players-list").style.display = '';
  

}

// Handle player selection and add/remove them from the requested players list
function handlePlayerSelection(event, user) {
  const selectedPlayerId = user.id;
  const selectedPlayerName = user.username;

  const currentPlayersContainer = document.getElementById('current-players-list');

  if (event.target.checked) {
    // Add selected player to the requested players list
    const playerDiv = document.createElement('div');
    playerDiv.className = 'selected-player';
    playerDiv.innerHTML = `
          <span>${selectedPlayerName} (Karma: ${user.karma})</span>
        `;
    currentPlayersContainer.appendChild(playerDiv);
  } else {
    // Remove player from the requested players list if checkbox is unchecked
    const players = currentPlayersContainer.getElementsByTagName('div');
    for (let playerDiv of players) {
      if (playerDiv.textContent.includes(selectedPlayerName)) {
        currentPlayersContainer.removeChild(playerDiv);
        break;
      }
    }
  }
}

// Submit the adventure form with selected players
document.getElementById('adventure-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const title = document.getElementById('title').value.trim();
  const description = document.getElementById('description').value.trim();
  const maxPlayers = parseInt(document.getElementById('max-players').value);

  // Get the selected players
  const selectedPlayerIds = Array.from(document.querySelector('#selector').selectedOptions).map(option => option.value);

  // Get the start and end dates from the form inputs
  const startDate = new Date(document.getElementById('start-date').value);
  const endDate = new Date(document.getElementById('end-date').value);


  // Validate the inputs
  if (!title || !description || selectedPlayerIds.length > maxPlayers) {
    Util.showToast('Please fill out all fields and select the correct number of players.', 'alert');
    return;
  }

  if (endDate < startDate) {
    Util.showToast('End date must be later or equal than the start date.', 'alert');
    return;
  }
  // Create the adventure object to send to the server

  const adventureData = {
    title,
    short_description: description,
    max_players: maxPlayers,
    requested_players: selectedPlayerIds,
    start_date: startDate.toISOString().split('T')[0], // Format as YYYY-MM-DD
    end_date: endDate.toISOString().split('T')[0], // Format as YYYY-MM-DD
    tags: "#tags",
    requested_room: "A"
  };

  // Send the request to the API
  const res = await fetch('api/adventures', {
    method: adventureMode,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(adventureData)
  });
  const data = await res.json(); // Parse the JSON body
  if (res.ok) {
    document.getElementById('adventure-form').reset();
    closeModal();
    loadAdventures(); // Reload adventures
    Util.showToast('Added adventure', 'confirm');
  } else if (res.status === 409) {
    console.warn('Misassigned players:', data.mis_assignments);
    Util.showToast(data.message || 'Some players could not be assigned.', 'alert');
    closeModal();
    loadAdventures(); // Reload adventures
  } else if (res.status === 401)  {
    Util.showToast('Please login to create a new adventure.')
  } else {
    Util.showToast('Failed to add adventure:'+ data.error);
  }
});


// Close modal when clicking outside
window.onclick = function (event) {
  const modal = document.getElementById('modal');
  if (event.target === modal) {
    closeModal();
  }
};


function updateUserUI() {
  const loginBtn = document.getElementById('login-button');
  const dropdown = document.getElementById('dropdown');
  if (currentUserName) {
    loginBtn.textContent = currentUserName;
    loginBtn.classList.add('logged-in');
    dropdown.classList.add('hidden');
  } else {
    loginBtn.textContent = 'Login';
    loginBtn.classList.remove('logged-in');
    dropdown.classList.add('hidden');
  }
}

function toggleDropdown() {
  const dropdown = document.getElementById('dropdown');
  dropdown.classList.toggle('hidden');
}

async function logout() {
  try {
    // 1) Tell the server to clear the cookie
    await fetch('api/logout', {
      method: 'GET',
      credentials: 'include'
    });
  } catch (err) {
    console.error('Error logging out on server:', err);
  }

  // 2) Clear any leftover client‐side state
  localStorage.removeItem('username');
  currentUserName = null;
  currentPrivilegeLevel = null;

  // 3) Update the UI
  updateUserUI();
  loadAdventures();
}

async function makeAssignments(action) {
  try {
    const res = await fetch('api/player-assignments', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message: action })  // message must match the key expected by the schema
    });
    const data = await res.json();

    if (res.ok) {
      loadAdventures();
      Util.showToast(`${action.charAt(0).toUpperCase() + action.slice(1)} triggered.`, 'confirm');
    } else {
      Util.showToast('Failed to assign players: ' + (data.message || data.error));
    }
  } catch (err) {
    console.error('Error during assignment action:', err);
    Util.showToast('Something went wrong.');
  }
}

async function updateKarma() {
  try {
    const res = await fetch('api/update-karma');
    if (res.ok) {
      loadAdventures();
      Util.showToast('Karma updated.', 'confirm');
    } else {
      const data = await res.json();
      Util.showToast('Failed to update karma: ' + data.message);
    }
  } catch (err) {
    console.error('Error updating karma:', err);
    Util.showToast('Something went wrong.');
  }
}

// Allow the drop action
function allowDrop(event) {
  event.preventDefault();
}

// Handle the drop action
async function drop(event) {
  event.preventDefault();

  // Get the player ID and the original and new adventure IDs
  const playerId = event.dataTransfer.getData('playerId');
  const fromAdventureId = event.dataTransfer.getData('fromAdventureId');
  const toPlayerList = event.target.closest('.player-list');
  const toAdventureId = toPlayerList.dataset.adventureId;

  // Update the player's adventure assignment on the backend
  const res = await fetch('api/player-assignments', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      player_id: playerId,
      from_adventure_id: fromAdventureId,
      to_adventure_id: toAdventureId
    })
  });

  if (res.ok) {
    // If successful, reload the adventures to reflect the change
    loadAdventures();
  } else {
    const data = await res.json();
    Util.showToast('Failed to update the assignment: ' + data.message);
  }
}

async function setCurrentUser() {
  try {
    const resp = await fetch('api/users/me', { credentials: 'include' });
    if (!resp.ok) {
      // Not logged in / unauthorized or server error — hide admin controls by default
      hideAdminControls();
      return;
    }

    const data = await resp.json();
    // fallback to `name` if display_name is missing/null, and default privilege to 0
    const displayName = data.display_name;
    const privilege = Number.isFinite(data.privilege_level)
      ? parseInt(data.privilege_level, 10)
      : (data.privilege_level != null ? Number(data.privilege_level) : 0);

    currentUserName = displayName;
    localStorage.setItem('username', displayName);
    currentPrivilegeLevel = Number.isFinite(privilege) ? privilege : 0;
    updateUserUI();

    if (currentPrivilegeLevel < 1) {
      hideAdminControls();
    }
  } catch (err) {
    console.error('Error fetching api/users/me:', err);
    // conservative default: hide admin controls
    hideAdminControls();
  }
}

function hideAdminControls() {
  ['make-assignments', 'release-assignments', 'reset-assignments', 'update-karma']
    .forEach(id => document.getElementById(id)?.classList.add('hidden'));
}