<template>
  <q-page>
    <div class="row items-center justify-center q-my-md q-mx-lg">
      <q-btn
        icon="chevron_left"
        aria-label="Earlier"
        color="primary"
        @click="switchWeek(-1)"
      ><span class="gt-sm">Earlier</span>
    </q-btn>
      <div class="text-h6 col-6 text-center">Wednesday {{ wednesdate }}</div>
      <q-btn
        icon-right="chevron_right"
        aria-label="Later"
        color="primary"
        @click="switchWeek(1)"
      ><span class="gt-sm">Later</span>
    </q-btn>
    </div>
    <q-spinner size="xl" v-if="loading" />
    <q-card v-else-if="adventures.length == 0" class="q-mx-lg">
      <q-card-section class="text-center">
        No sessions this week yet. Make one!
      </q-card-section>
    </q-card>
    <div v-else class="row justify-evenly q-col-gutter-lg">
      <div
        class="col-xs-12 col-sm-6 col-md-4 col-lg-3"
        v-for="a in adventures"
        :key="a.id"
      >
        <q-card v-if="!isWaitinglist(a)" class="q-ma-md">
          <q-card-section class="q-gutter-md">
            <q-btn
              v-if="me && (me.id == a.user_id || me.privilege_level >= 2)"
              icon="edit"
              round
              color="accent"
              @click="
                editAdventure = a;
                addAdventure = true;
              "
              class="float-right"
            />
            <div class="text-h6 text-center">{{ a.title }}</div>
            <q-separator />

            <div class="row justify-between">
              <div>{{ describeDuration(a) }}</div>
              <q-chip
                v-for="t in a.tags?.split(',')"
                :key="t"
                :label="t"
                color="accent"
                text-color="white"
                :ripple="false"
                class="float-right"
              />
              <div v-if="a.requested_room">Room: {{ a.requested_room }}</div>
            </div>
            <div class="description">
              <template v-if="a.short_description">{{
                a.short_description
              }}</template
              ><i v-else>No description</i>
            </div>
            <div class="row justify-between">
              <q-rating
                v-model="a.rank_combat"
                :max="3"
                readonly
                size="2em"
                icon="img:spiked-dragon-head.svg"
              />
              <q-rating
                v-model="a.rank_exploration"
                :max="3"
                readonly
                size="2em"
                icon="img:dungeon-gate.svg"
              />
              <q-rating
                v-model="a.rank_roleplaying"
                :max="3"
                readonly
                size="2em"
                icon="img:drama-masks.svg"
              />
            </div>
            <q-list v-if="me?.privilege_level >= 2" class="adminDropTarget">
              <Container
                :class="['q-pa-md', 'rounded-borders', { 'grid-container': a.assignments.length > 0 }]"
                @drop="(dr) => onDrop(dr, a.id)"
                group-name="assignedPlayers"
                :get-child-payload="
                  (n) => ({
                    from_adventure: a.id,
                    user_id: a.assignments[n].user.id,
                  })
                "
              >
                <template v-if="a.assignments.length > 0">
                  <Draggable v-for="p in a.assignments" :key="p.user.id">
                    <q-item class="items-center round-borders character">
                      <q-avatar size="sm" class="q-mr-sm">
                        <img :src="p.user.profile_pic" />
                      </q-avatar>
                      <div class="q-mr-sm">
                        {{ p.user.display_name }} ({{ p.user.karma }})
                      </div>
                      <q-btn
                        size="sm"
                        :icon="p.appeared ? 'check' : 'close'"
                        round
                        :color="p.appeared ? 'positive' : 'negative'"
                        class="q-mr-sm flat"
                        @click="togglePresence(a.id, p)"
                      />
                    </q-item>
                  </Draggable>
                </template>
                <template v-else>
                  <q-item
                    class="text-subtitle1 text-center none-list non-selectable"
                  >
                    No players assigned yet
                  </q-item>
                </template>
              </Container>
            </q-list>
            <q-list v-else>
              <Container class="q-pa-md rounded-borders grid-container">
                <q-item v-for="p in a.assignments" :key="p.user.id">
                  <q-item class="items-center">
                    <q-avatar size="sm" class="q-mr-sm">
                      <img :src="p.user.profile_pic" />
                    </q-avatar>
                    <div>
                      {{ p.user.display_name }}
                    </div>
                    <q-btn
                      size="sm"
                      round
                      class="q-mr-sm flat"
                      label="Cancel Assignment"
                      @click="cancleAssignment(a.id, p)"
                    />
                  </q-item>
                </q-item>
              </Container>
            </q-list>
            <div class="container">
              <div class="row justify-center q-gutter-sm">
                <q-btn
                  v-for="n in 3"
                  class="col"
                  style="max-width: 8rem;"
                  :key="n"
                  icon="person_add"
                  :label="`${n}`"
                  color="primary"
                  :outline="mySignups[a.id] === n"
                  @click="signup(a, n)"
                />
              </div>
              <div class="row justify-center q-my-md">
                <q-btn
                  label="More details"
                  icon="info"
                  @click="focussed = a"
                  color="primary"
                />
              </div>
            </div>
          </q-card-section>
        </q-card>
        <q-card v-else class="q-ma-md waitinglist">
          <q-card-section class="q-gutter-md">
            <div class="text-h6 text-center">{{ a.title }}</div>
            <q-separator />
            <q-list v-if="me?.privilege_level >= 2" class="adminDropTarget">
              <Container
                class="q-pa-md rounded-borders"
                @drop="(dr) => onDrop(dr, a.id)"
                group-name="assignedPlayers"
                :get-child-payload="
                  (n) => ({
                    from_adventure: a.id,
                    user_id: a.assignments[n].user.id,
                  })
                "
              >
                <Draggable v-for="p in a.assignments" :key="p.user.id">
                  <q-item class="items-center round-borders character">
                    <q-avatar size="sm" class="q-mr-sm">
                      <img :src="p.user.profile_pic" />
                    </q-avatar>
                    <div class="q-mr-sm">
                      {{ p.user.display_name }} ({{ p.user.karma }})
                    </div>
                    <q-btn
                      size="sm"
                      round
                      color="negative"
                      class="q-mr-sm flat"
                      label="Cancel Assignment!"
                      @click="cancelAssignment(p.id)"
                    />
                  </q-item>
                </Draggable>
              </Container>
            </q-list>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-page-sticky position="bottom" :offset="[0, 18]">
      <q-btn
        v-if="me"
        fab
        label="Make a new Adventure"
        icon="add"
        color="accent"
        @click="
          editAdventure = null;
          addAdventure = true;
        "
      />
    </q-page-sticky>

    <q-dialog :modelValue="!!focussed" @hide="focussed = null">
      <q-card style="min-width: 300px">
        <q-card-section>
          <div class="text-h6">{{ focussed.title }}</div>
          <q-separator />
          <q-chip
            v-for="t in focussed.tags?.split(',')"
            :key="t"
            :label="t"
            color="accent"
            text-color="white"
            :ripple="false"
          />
          <q-markup-table flat class="q-mb-md">
            <tr>
              <td>DM</td>
              <td>{{ focussed.creator.display_name }}</td>
            </tr>
            <tr>
              <td>Duration</td>
              <td>{{ describeDuration(focussed) }}</td>
            </tr>
            <tr>
              <td>Max players</td>
              <td>{{ focussed.max_players }}</td>
            </tr>
            <tr>
              <td>Combat</td>
              <td>
                <q-rating
                  v-model="focussed.rank_combat"
                  :max="3"
                  readonly
                  size="2em"
                  icon="img:spiked-dragon-head.svg"
                />
              </td>
            </tr>
            <tr>
              <td>Exploration</td>
              <td>
                <q-rating
                  v-model="focussed.rank_exploration"
                  :max="3"
                  readonly
                  size="2em"
                  icon="img:dungeon-gate.svg"
                />
              </td>
            </tr>
            <tr>
              <td>Roleplaying</td>
              <td>
                <q-rating
                  v-model="focussed.rank_roleplaying"
                  :max="3"
                  readonly
                  size="2em"
                  icon="img:drama-masks.svg"
                />
              </td>
            </tr>
            <tr v-if="focussed.requested_room">
              <td>Room</td>
              <td>{{ focussed.requested_room }}</td>
            </tr>
          </q-markup-table>
          <div class="description">
            <template v-if="focussed.short_description">{{
              focussed.short_description
            }}</template
            ><i v-else>No description</i>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-actions class="justify-end">
          <q-btn
            label="Cancel signup"
            color="negative"
            v-if="focussed.id in mySignups"
            class="q-mr-md"
            @click="signup(focussed, mySignups[focussed.id])"
          />
          <q-btn-dropdown
            split
            color="primary"
            label="Sign up"
            content-class="q-px-lg"
            @click="signup(focussed, 1)"
            :loading="saving"
          >
            <q-list>
              <template v-for="n in [1, 2, 3]" :key="n">
                <q-item
                  clickable
                  v-close-popup
                  @click="signup(focussed, n)"
                  :disable="mySignups[focussed.id] == n"
                >
                  <q-item-section avatar v-if="focussed.id in mySignups">
                    <q-avatar
                      icon="check"
                      text-color="positive"
                      v-if="mySignups[focussed.id] == n"
                    />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ choiceLabels[n] }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-list>
          </q-btn-dropdown>
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="addAdventure" :persistent="addingAdventure">
      <div class="col-8">
        <AddAdventure
          @eventChange="eventChange"
          @canClose="(v) => (addingAdventure = !v)"
          :editExisting="editAdventure"
        />
      </div>
    </q-dialog>
  </q-page>
</template>

<style lang="scss" scoped>
.description {
  background-color: $dark;
  border: 1px solid;
  border-radius: 4px;
  padding: 8px;
}
.adminDropTarget {
  border-radius: 4px;
  background-color: $secondary;
}
.character {
  border: 1px solid;
  border-radius: 4px;
  cursor: grab;
}
.waitinglist {
  background-color: $dark-page;
  height: 95%;
}
.grid-container {
  column-count: 2;
  column-gap: 12px;
}
.grid-container > * {
  break-inside: avoid;
}
</style>

<script lang="ts">
import { defineComponent, inject } from 'vue';
import { Container, Draggable } from 'vue3-smooth-dnd';
import AddAdventure from '../components/AddAdventure.vue';

export default defineComponent({
  name: 'IndexPage',
  components: { AddAdventure, Container, Draggable },
  emits: ['setErrors', 'startAdminAction', 'finishAdminAction'],
  setup() {
    return {
      me: inject('me') as any,
      forceRefresh: inject('forceRefresh') as number,
      choiceLabels: {
        1: 'First choice',
        2: 'Second choice',
        3: 'Third choice',
      },
    };
  },
  data() {
    let start = new Date();
    if (start.getDay() > 3) {
      start.setDate(start.getDate() + 7);
    }
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    return {
      weekStart: start.toISOString().split('T')[0],
      adventures: [],
      focussed: null as any,
      addAdventure: false,
      addingAdventure: false,
      loading: false,
      saving: false,
      editAdventure: null,
      mySignups: {} as { [adventure_id: number]: 1 | 2 | 3 }, 
    };
  },
  methods: {
    async fetch(reloadSignups: boolean) {
      try {
        this.loading = true;
        const req1 = this.$api.get(
          '/api/adventures?week_start=' +
            this.weekStart +
            '&week_end=' +
            this.weekEnd
        );
        if (this.me && reloadSignups) {
          const resp = await this.$api.get('/api/signups?user=' + this.me.id);
          this.mySignups = {};
          for (const { adventure_id, priority } of resp.data) {
            this.mySignups[adventure_id] = priority;
          }
        }
        const resp = await req1;
        this.adventures = resp.data;
      } catch (e) {
        this.$emit('setErrors', this.$extractErrors(e));
      } finally {
        this.loading = false;
      }
    },
    async signup(e: { date: string; id: string }, prio: number) {
      const dateIsInPast = new Date().getTime() > new Date(e.date).getTime();
      if (dateIsInPast) {
        this.$q.notify({
          message:
            'You cannot sign up for sessions that have already happened.',
          type: 'negative',
        });
        return;
      }

      try {
        this.saving = true;
        await this.$api.post('/api/signups', {
          adventure_id: e.id,
          priority: prio,
        });
        this.$q.notify({
          message: 'Your signup is submitted!',
          type: 'positive',
        });
        await this.fetch(true);
      } finally {
        this.saving = false;
      }
    },
    eventChange() {
      this.addAdventure = false;
      this.fetch(false);
    },
    switchWeek(offset: number) {
      const d = new Date(this.weekStart);
      d.setDate(d.getDate() + offset * 7);
      this.weekStart = d.toISOString().split('T')[0];
    },
    describeDuration(a: { num_sessions: number }): string {
      if (a.num_sessions == 1) {
        return 'One shot';
      }
      return a.num_sessions + ' weeks';
    },
    isWaitinglist(a: { id: number }): boolean {
      return a.id == -999;
    },
    cancelAssignment(adventure_id: number) {
      this.$q
        .dialog({
          title: 'Cancel Assignment',
          message:
            'Are you sure you want to give up your place on this adventure? You will not be able to reclaim it and the place will be assigned to someone else. Please note that this option is only for emergency',
          cancel: true,
        })
        .onOk(async () => {
          await this.$api.delete('/api/adventures/' ,{
             data: {adventure_id: adventure_id,},
          });
          this.$q.notify({
            message: "And you're off!",
            type: 'positive',
          });
        });
    },

    async togglePresence(adventure_id: number, assignment: any) {
      assignment.appeared = !assignment.appeared;
      await this.$api.post('/api/player-assignments', {
        adventure_id: adventure_id,
        user_id: assignment.user.id,
        appeared: assignment.appeared,
      });
    },
    async onDrop(
      dropResult: {
        payload: { from_adventure: number; user_id: number };
        addedIndex: null | number;
        removedIndex: null | number;
      },
      toAdventure: number
    ) {
      if (dropResult.addedIndex === null) {
        // Ignore this event. We'll get one targetting the actual destination contianer.
        return;
      }
      this.$emit('startAdminAction');
      try {
        await this.$api.patch('/api/player-assignments', {
          player_id: dropResult.payload.user_id,
          from_adventure_id: dropResult.payload.from_adventure,
          to_adventure_id: toAdventure,
        });
      } finally {
        this.$emit('finishAdminAction');
      }
      this.fetch(false);
    },
  },
  computed: {
    wednesdate() {
      const d = new Date(this.weekStart);
      d.setDate(d.getDate() + 2);

      const result = d.toISOString().split('T')[0];
      const today = new Date().toISOString().split('T')[0];

      return result === today ? 'this week' : result;
    },
    weekEnd() {
      const d = new Date(this.weekStart);
      d.setDate(d.getDate() + 6);
      return d.toISOString().split('T')[0];
    },
  },
  watch: {
    weekStart: {
      async handler() {
        await this.fetch(false);
      },
      immediate: true,
    },
    forceRefresh() {
      this.fetch(true);
    },
  },
});
</script>
