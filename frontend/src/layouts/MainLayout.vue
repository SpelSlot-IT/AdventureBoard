<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar class="row justify-between">
        <div class="q-gutter-x-md">
          <q-btn label="Home" icon="home" to="/" />
          <q-btn label="Characters" icon="sym_o_chess_pawn" to="/characters" />
        </div>
        <q-avatar icon="img:spelslot-logo.svg" size="50px"></q-avatar>
        <div>
          <q-toggle label="Noob" v-if="me?.privilege_level > 0 || droppedPrivileges" color="secondary" :modelValue="droppedPrivileges" @update:modelValue="togglePrivileges" />
          <q-spinner size="lg" v-if="adminActionsActive > 0" />
          <q-btn
            v-if="me"
            :icon="me.profile_pic ? 'img:' + me.profile_pic : 'settings'"
            :label="me.display_name"
          >
            <q-menu>
              <q-list style="min-width: 100px">
                <q-item to="/profile">
                  <q-item-section>Edit profile</q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="logout">
                  <q-item-section>Log out</q-item-section>
                </q-item>
                <template v-if="me.privilege_level >= 2">
                  <q-item
                    clickable
                    v-close-popup
                    @click="adminAction('assign')"
                  >
                    <q-item-section>Make assignments</q-item-section>
                  </q-item>
                  <q-item
                    clickable
                    v-close-popup
                    @click="adminAction('reassign')"
                  >
                    <q-item-section>Reassigne players form the waitinglist</q-item-section>
                  </q-item>
                  <q-item
                    clickable
                    v-close-popup
                    @click="adminAction('release')"
                  >
                    <q-item-section>Release assignments</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="adminAction('reset')">
                    <q-item-section>Unrelease assignments</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="updateKarma()">
                    <q-item-section>Update karma</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="signups">
                    <q-item-section>See current signups</q-item-section>
                  </q-item>
                </template>
              </q-list>
            </q-menu>
          </q-btn>
          <q-btn v-else label="Login" @click="login" icon="login" />
          <q-btn
            class="q-ml-sm"
            color="primary"
            @click="toggleDarkMode"
            :icon="darkModeIcon"
          />
        </div>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page v-if="errors.length > 0" class="q-px-lg q-pt-md">
        <q-banner v-for="e in errors" :key="e" class="bg-negative" rounded>{{
          e
        }}</q-banner>
      </q-page>
      <q-page v-else-if="loading" class="q-px-lg q-pt-md">
        <q-spinner size="xl" />
      </q-page>
      <router-view
        v-else
        @setErrors="(es) => (errors = es)"
        @changedUser="fetchMe"
        @mustLogin="login"
        @startAdminAction="adminActionsActive++"
        @finishAdminAction="adminActionsActive--"
      />
      <span v-if="version" class="fixed-bottom-left q-ml-sm">
        AdventureBoard v{{ version }} 
      </span>
      <a href="https://github.com/SpelSlot/AdventureBoard" class="fixed-bottom-right q-mr-sm">
        <q-icon name="github" size="lg" />
      </a>
    </q-page-container>
  </q-layout>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { isAxiosError } from 'axios';

export default defineComponent({
  name: 'MainLayout',

  data() {
    return {
      loading: true,
      errors: [] as string[],
      version: '',
      adminActionsActive: 0,
      forceRefresh: 1,
      droppedPrivileges: false,
      me: null as null | {
        id: number;
        display_name: string;
        world_builder_name: string;
        dnd_beyond_name: string;
        dnd_beyond_campaign: number;
        privilege_level: number;
        profile_pic: string;
      },
    };
  },

  methods: {
    toggleDarkMode() {
      const darkModeEnabled = !this.$q.dark.isActive;
      localStorage.setItem('darkMode', String(+darkModeEnabled));
      this.$q.dark.set(darkModeEnabled);
    },
    async fetchMe() {
      this.me = (await this.$api.get('/api/users/me')).data;
      if(this.droppedPrivileges) {
        this.me!.privilege_level = 0;
      }
    },
    async logout() {
      const currentUrl = window.location.href;
      window.location.href = `/api/logout?next=${encodeURIComponent(
        currentUrl
      )}`;
    },
    async login() {
      const currentUrl = window.location.href;
      window.location.href = `/api/login?next=${encodeURIComponent(
        currentUrl
      )}`;
    },
    async signups() {
      window.location.href = '/#/signups';
    },

    async adminAction(action: string) {
      this.adminActionsActive++;
      try {
        await this.$api.put('/api/player-assignments', { action: action });
        this.forceRefresh++;
        this.$q.notify({
          message: `${
            action.charAt(0).toUpperCase() + action.slice(1)
          } triggered.`,
          type: 'positive',
        });
      } finally {
        this.adminActionsActive--;
      }
    },
    async updateKarma() {
      this.adminActionsActive++;
      try {
        await this.$api.post('/api/update-karma');
        this.forceRefresh++;
        this.$q.notify({
          message: 'Karma updated.',
          type: 'positive',
        });
      } finally {
        this.adminActionsActive--;
      }
    },
    async optionallyFetchUser() {
      try {
        await this.fetchMe();
      } catch (e) {
        if (isAxiosError(e) && e.response?.status == 401) {
          // Not logged in. That's fine.
        } else {
          throw e;
        }
      }
    },
    togglePrivileges(v: boolean) {
      this.droppedPrivileges = v;
      if(v) {
        this.me!.privilege_level = 0;
      } else {
        this.fetchMe();
      }
    },
  },

  async beforeMount() {
    this.loading = true;
    try {
      const preferredTheme =
        localStorage.getItem('darkMode') === null 
        ? 'auto' 
        : Boolean(Number(localStorage.getItem('darkMode')));
      this.$q.dark.set(preferredTheme);

      const aliveReq = this.$api.get('/api/alive');
      const meReq = this.optionallyFetchUser();
      const aliveResp = await aliveReq;
      if (aliveResp.data.status != 'ok') {
        this.errors = ['Service is unavailable'];
      }
      this.version = aliveResp.data.version;
      await meReq;
    } finally {
      this.loading = false;
    }
  },

  provide() {
    return {
      me: computed(() => this.me),
      forceRefresh: computed(() => this.forceRefresh),
    };
  },
  computed: {
    darkModeIcon: function () {
      return this.$q.dark.isActive ? 'wb_sunny' : 'brightness_2';
    },
  },
  watch: {
    '$route.fullPath'() {
      this.errors = [];
    },
  },
});
</script>
