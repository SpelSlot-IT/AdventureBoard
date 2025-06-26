// ——— Globals & Helpers ———
var currentWeekOffset = 0;
var currentUserName = null; // track logged in user
var currentPrivilegeLevel = null; // track privilege_level
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


function handleLoginClick() {
  if (!currentUserName) {
    window.location.href = "login";
  } else {
    toggleDropdown();
  }
}

function openHelp()
{
  window.location.href = "help";
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

async function loadAdventures() {
  updateWeekLabel();
  const [weekStart, weekEnd] = getWeekRange(currentWeekOffset);

  // Build the query string
  const params = new URLSearchParams();
  params.set('user', currentUserName);
  params.set('adventure_id', null);
  // always include week bounds
  params.set('week_start', weekStart.toISOString().split('T')[0]);
  params.set('week_end', weekEnd.toISOString().split('T')[0]);

  // 1) fetch data 
  const [advRes, signupRes] = await Promise.all([
    fetch(`api/adventures?${params.toString()}`),
    fetch(`api/signups?user=${currentUserName}`)
  ]);
  const adventures = await advRes.json();
  const userSignups = await signupRes.json();

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

      const title = adventure.title.length > 16 ? adventure.title.slice(0, 16) + '…' : adventure.title;
      const desc = adventure.short_description.length > 64 ? adventure.short_description.slice(0, 64) + '…' : adventure.short_description;

      const signedPriority = userSignups[adventure.id];
      const getHighlight = (prio) => signedPriority === prio ? 'highlighted' : '';

      const playerList = adventure.players?.length > 0
        ? adventure.players.map(player => `
                <div class="draggable-player ${player.username === currentUserName ? 'own-player' : ''}"
                    draggable="true"
                    data-player-id="${player.id}"
                    data-adventure-id="${adventure.id}">
                  <span class="player-name">${player.username.slice(0, 16)}</span><br>
                  <span class="player-karma">${player.karma} ✨</span>
                </div>
              `).join('')
        : 'No players assigned yet';

      card.innerHTML = `
            <h2>${title}</h2>
            <p>${desc}</p>
            <p><strong>Players:</strong>
              <div class="player-list" 
                  data-adventure-id="${adventure.id}" 
                  ondrop="drop(event)" 
                  ondragover="allowDrop(event)">
                ${playerList}
              </div>
            </p>
            <div >
              <button style="width: 140px;" onclick="moreDetails(${adventure.id})">More Details</button>
              <div style="margin-top: 10px;">
                <button class="${getHighlight(1)}" onclick="signUp(this, ${adventure.id}, 1)">🥇</button>
                <button class="${getHighlight(2)}" onclick="signUp(this, ${adventure.id}, 2)">🥈</button>
                <button class="${getHighlight(3)}" onclick="signUp(this, ${adventure.id}, 3)">🥉</button>
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

  // 5) re-attach drag handlers
  container.querySelectorAll('.draggable-player').forEach(el => {
    el.addEventListener('dragstart', e => {
      e.dataTransfer.setData('playerId', e.target.dataset.playerId);
      e.dataTransfer.setData('fromAdventureId', e.target.dataset.adventureId);
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



async function signUp(btn, adventureId, priority) {
  const res = await fetch('api/signups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user: currentUserName, adventure_id: adventureId, priority })
  });

  if (res.ok) {
    loadAdventures(); // refresh to update button highlights
  } else {
    showToast('Failed to sign up: Are you logged in?');
  }
}

async function moreDetails(adventure_id) {
  document.getElementById('modal').style.display = 'block';
  document.getElementById("open-player-select").style.visibility='hidden';
  document.getElementById("current-players-list").style.display = 'none';
  const params = new URLSearchParams();
  params.set('adventure_id', adventure_id);
  const res = await fetch(`api/adventures?${params.toString()}`);
  if (res.ok) {
    const data = await res.json();
    document.getElementById('title').textContent = data.adventure.name;
    document.getElementById('description').textContent = data.adventure.description;
    document.getElementById('creator').textContent = data.adventure.creator;
    document.getElementById('start-date').textContent = data.adventure.start_date;
    document.getElementById('end-date').textContent = data.adventure.end_date;
    document.getElementById('max-players').textContent = data.adventure.max_players;

    // Example condition: lock fields if adventure is archived
    if (currentUserName !== data.adventure.creator) {
      const fields = ['title', 'description', 'creator', 'start-date', 'end-date', 'max-players'];
      fields.forEach(id => {
        const el = document.getElementById(id);
        
        // Disable input fields or make non-editable
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') {
          el.disabled = true;
        } else {
          el.setAttribute('contenteditable', 'false'); // For div/span/etc.
        }
      });
    }
  }
}

// Open the modal and load available players
async function openModal() {
  if (!currentUserName) {
    showToast("Please login to create a new adventure.", "alert");
    return;
  }
  document.getElementById('modal').style.display = 'block';
  document.getElementById('creator').value = currentUserName; // set creator name
  document.getElementById("open-player-select").style.visibility='visible';
  document.getElementById("current-players-list").style.display = 'none';
  initializeDateFields();
}

// Close the modal
function closeModal() {
  document.getElementById('modal').style.display = 'none';
  //initializeDateFields(); // reset date fields
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
    showToast("Failed to load user list:" + err);
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
    showToast('Please fill out all fields and select the correct number of players.', 'alert');
    return;
  }

  if (endDate < startDate) {
    showToast('End date must be later or equal than the start date.', 'alert');
    return;
  }
  // Create the adventure object to send to the server

  const adventureData = {
    title,
    short_description: description,
    creator_id: currentUserName, // creator
    max_players: maxPlayers,
    requested_players: selectedPlayerIds,
    start_date: startDate.toISOString().split('T')[0], // Format as YYYY-MM-DD
    end_date: endDate.toISOString().split('T')[0] // Format as YYYY-MM-DD
  };

  // Send the request to the API
  const res = await fetch('api/adventures', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(adventureData)
  });
  const data = await res.json(); // Parse the JSON body
  if (res.ok) {
    document.getElementById('adventure-form').reset();
    closeModal();
    loadAdventures(); // Reload adventures
    showToast('Added adventure', 'confirm');
  } else if (res.status === 409) {
    console.warn('Misassigned players:', data.mis_assignments);
    showToast(data.message || 'Some players could not be assigned.', 'alert');
    closeModal();
    loadAdventures(); // Reload adventures
  } else {
    showToast('Failed to add adventure:'+ data.error);
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
    await fetch('logout', {
      method: 'POST',
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


function changePassword() {
  showToast('Password page not implemented yet.', 'alert');
}

async function registerNewUser() {
  if (!currentUserName) {
    showToast("No user is logged in.");
    return;
  }

  // Try to register the user
  const res = await fetch('api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: currentUserName })
  });

  if (res.ok) {
    const data = await res.json();
    showToast(`User ${currentUserName} registered successfully with ID ${data.user_id}`, 'confirm');
  } else {
    const errorData = await res.json();
    showToast(`Error: ${errorData.error}`);
  }
}



async function refreshAssignments() {
  try {
    const res = await fetch("api/adventure-assignment", {
      method: 'PUT'
    });
    if (res.ok) {
      loadAdventures();
      showToast('Assignments refreshed.', 'confirm');
    } else {
      const data = await res.json();
      showToast('Failed to assign players: ' + data.message);
    }
  } catch (err) {
    console.error('Error refreshing assignments:', err);
    showToast('Something went wrong.');
  }
}

async function updateKarma() {
  try {
    const res = await fetch('api/update-karma');
    if (res.ok) {
      loadAdventures();
      showToast('Karma updated.', 'confirm');
    } else {
      const data = await res.json();
      showToast('Failed to update karma: ' + data.message);
    }
  } catch (err) {
    console.error('Error updating karma:', err);
    showToast('Something went wrong.');
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
  const res = await fetch('api/adventure-assignment', {
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
    showToast('Failed to update the assignment: ' + data.message);
  }
}

async function setCurrentUser() {
  const resp = await fetch('api/me', { credentials: 'include' });
  if (resp.ok) {
    const { user_name, privilege_level } = await resp.json();
    currentUserName = user_name;
    localStorage.setItem('username', user_name);
    currentPrivilegeLevel = privilege_level
    updateUserUI();
  }
  if (currentPrivilegeLevel < 1) {
    document.getElementById('refresh-assignments').classList.add('hidden');
    document.getElementById('update-karma').classList.add('hidden');
  }
}