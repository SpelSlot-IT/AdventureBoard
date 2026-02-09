<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">Frequently Asked Questions</div>
    <q-list bordered class="rounded-borders">
      <q-expansion-item
        expand-separator
        icon="sym_o_stars"
        label="How do I earn karma?"
      >
        <q-card>
          <q-card-section>
            <div class="text-body2">
              <p><strong>As a DM:</strong></p>
              <ul>
                <li>+500 karma for creating and running a session</li>
              </ul>
              <p><strong>As a Player:</strong></p>
              <ul>
                <li>+100 karma for attending your 1st choice session</li>
                <li>+120 karma for attending your 2nd choice session</li>
                <li>+140 karma for attending your 3rd choice session</li>
                <li>+150 karma for attending a session you were assigned to outside your top 3 choices</li>
                <li>+200 karma for attending from the waiting list</li>
                <li>+180 karma for being on the waiting list but not attending</li>
              </ul>
              <p class="q-mt-sm text-caption">
                Note: Sessions marked as "excluded from karma generation" (typically the first week of each month) do not award karma.
              </p>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <q-expansion-item
        expand-separator
        icon="sym_o_remove_circle"
        label="How do I lose karma?"
      >
        <q-card>
          <q-card-section>
            <div class="text-body2">
              <ul>
                <li>-500 karma for not appearing to a session you were assigned to (non-waiting list sessions only)</li>
              </ul>
              <p class="q-mt-sm text-caption">
                Note: If you need to cancel, try to do so as early as possible. Last-minute cancellations may result in additional penalties.
              </p>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <q-expansion-item
        expand-separator
        icon="sym_o_schedule"
        label="What to do when I wasn't in a session for a long time?"
      >
        <q-card>
          <q-card-section>
            <div class="text-body2">
              <p>
                If you've been away for a while, simply sign up for upcoming sessions like normal! 
                The assignment system considers your karma when matching players to sessions, so 
                players with higher karma get priority for their preferred sessions.
              </p>
              <p class="q-mt-sm">
                Make sure your profile is complete (especially your D&D Beyond name) before signing up, 
                as incomplete profiles may prevent you from being assigned.
              </p>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <q-expansion-item
        expand-separator
        icon="sym_o_help"
        label="I was not assigned to the session I wanted, what to do?"
      >
        <q-card>
          <q-card-section>
            <div class="text-body2">
              <p>
                The assignment system works in rounds, prioritizing players first by their signup priority 
                (1st choice beats 2nd choice, which beats 3rd choice), and then by karma within each priority 
                level. If you weren't assigned to your preferred session:
              </p>
              <ul>
                <li>You may have been assigned to another session you signed up for</li>
                <li>You may have been placed on the waiting list</li>
                <li>Players who marked it as a higher priority (1st vs your 2nd/3rd) got priority, even if you have more karma</li>
                <li>Within the same priority level, higher karma players got priority</li>
              </ul>
              <p class="q-mt-sm">
                <strong>What you can do:</strong>
              </p>
              <ul>
                <li>Check if you're on the waiting list - admins can reassign players if spots open up</li>
                <li>Attend the session you were assigned to - this helps maintain your karma</li>
                <li>Make sure to prioritize your most wanted sessions as 1st choice - priority matters more than karma!</li>
                <li>Build your karma by consistently attending sessions to improve your chances within each priority level</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <q-expansion-item
        expand-separator
        icon="sym_o_info"
        label="Is TEZ a normal session?"
      >
        <q-card>
          <q-card-section>
            <div class="text-body2">
              <p>
                TEZ (or any special event session) follows the same rules as regular sessions unless 
                specifically marked otherwise. Check the session details:
              </p>
              <ul>
                <li>If it's marked as "excluded from karma generation", it won't affect karma</li>
                <li>Otherwise, normal karma rules apply (attendance bonuses, penalties for no-shows, etc.)</li>
              </ul>
              <p class="q-mt-sm">
                When in doubt, ask an admin or check the session description for any special notes.
              </p>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <q-expansion-item
        expand-separator
        icon="sym_o_priority"
        label="How does the signup priority system work?"
      >
        <q-card>
          <q-card-section>
            <div class="text-body2">
              <p>
                When signing up for sessions, you can assign priorities 1, 2, or 3 to different sessions. 
                The assignment system processes players in multiple rounds:
              </p>
              <ol>
                <li>DM-requested players who signed up</li>
                <li>Players continuing from previous sessions</li>
                <li>Story players sorted by karma</li>
                <li>
                  All players ranked by karma, assigned to their highest priority available session.
                  <strong>This step is subdivided by priority:</strong>
                  <ul class="q-mt-xs">
                    <li>First, all 1st choice signups are processed (ranked by karma, highest first)</li>
                    <li>Then, all 2nd choice signups are processed (ranked by karma, highest first)</li>
                    <li>Finally, all 3rd choice signups are processed (ranked by karma, highest first)</li>
                  </ul>
                  <p class="q-mt-xs">
                    <strong>Important:</strong> A player with a 1st choice will always get priority over 
                    someone with a 2nd choice, regardless of karma differences. Within the same priority 
                    level, higher karma wins.
                  </p>
                </li>
                <li>Remaining players assigned to any available session</li>
                <li>Everyone else goes to the waiting list</li>
              </ol>
              <p class="q-mt-sm">
                Your priority choices matter more than karma - always put your most wanted sessions as 
                priority 1, 2, and 3!
              </p>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <q-expansion-item
        expand-separator
        icon="sym_o_cancel"
        label="Can I cancel my assignment?"
      >
        <q-card>
          <q-card-section>
            <div class="text-body2">
              <p>
                Yes, but use this feature carefully! You can cancel your own assignment by clicking 
                the delete button next to your name on a session card.
              </p>
              <p class="q-mt-sm">
                <strong>Important:</strong>
              </p>
              <ul>
                <li>This is intended for emergencies only</li>
                <li>You cannot reclaim your spot after canceling</li>
                <li>The spot will be reassigned to someone else</li>
                <li>Not showing up without canceling results in -500 karma</li>
              </ul>
              <p class="q-mt-sm">
                If you need to cancel, try to do so as early as possible so admins can reassign your spot.
              </p>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>
    </q-list>
  </q-page>
</template>
