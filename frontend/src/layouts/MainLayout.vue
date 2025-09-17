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
                    @click="adminAction('release')"
                  >
                    <q-item-section>Release assignments</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="adminAction('reset')">
                    <q-item-section>Reset assignments</q-item-section>
                  </q-item>
                  <q-item clickable v-close-popup @click="updateKarma()">
                    <q-item-section>Update karma</q-item-section>
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
      <span v-if="version" class="fixed-bottom-left q-ml-sm"
        >AdventureBoard v{{ version }}</span
      >
    </q-page-container>
  </q-layout>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { isAxiosError } from 'axios';
import { Dark } from 'quasar';

export default defineComponent({
  name: 'MainLayout',

  data() {
    return {
      loading: true,
      errors: [] as string[],
      version: '',
      adminActionsActive: 0,
      forceRefresh: 1,
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
      Dark.set(!Dark.isActive);
    },
    async fetchMe() {
      this.me = (await this.$api.get('/api/users/me')).data;
    },
    logout() {
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

    async adminAction(message: string) {
      this.adminActionsActive++;
      try {
        await this.$api.put('/api/player-assignments', { message: message });
        this.forceRefresh++;
        this.$q.notify({
          message: `${
            message.charAt(0).toUpperCase() + message.slice(1)
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
        await this.$api.get('/api/update-karma');
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
  },

  async beforeMount() {
    this.loading = true;
    try {
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
    darkModeIcon: () => (Dark.isActive ? 'wb_sunny' : 'brightness_2'),
  },
  watch: {
    '$route.fullPath'() {
      this.errors = [];
    },
  },
});
</script>
