<template>
  <q-page class="row items-center justify-evenly">
    <q-form @submit="save" class="col-8">
      <q-card>
        <q-card-section class="q-gutter-lg">
          <div class="text-h6">User profile</div>
          <q-input v-model="display_name" label="Display name" />
          <q-input v-model="world_builder_name" label="World builder name" />
          <q-input v-model="dnd_beyond_name" label="D&D Beyond name" />
          <div>D&D Beyond campaign: {{ me?.dnd_beyond_campaign }}</div>
          <q-separator class="q-my-md" />
<div class="text-subtitle1 text-weight-bold">Notification Preferences</div>
<q-list class="q-gutter-sm">
  <q-item tag="label" v-ripple>
    <q-item-section>
      <q-item-label>New Adventures</q-item-label>
      <q-item-label caption>Alert me when a new game is posted</q-item-label>
    </q-item-section>
    <q-item-section side>
      <q-toggle v-model="notify_new_adventure" color="primary" />
    </q-item-section>
  </q-item>

  <q-item tag="label" v-ripple>
    <q-item-section>
      <q-item-label>Deadline Reminders</q-item-label>
      <q-item-label caption>4-hour warning if I haven't signed up</q-item-label>
    </q-item-section>
    <q-item-section side>
      <q-toggle v-model="notify_deadline" color="primary" />
    </q-item-section>
  </q-item>

  <q-item tag="label" v-ripple>
    <q-item-section>
      <q-item-label>Party Assignments</q-item-label>
      <q-item-label caption>Notify me when parties are finalized</q-item-label>
    </q-item-section>
    <q-item-section side>
      <q-toggle v-model="notify_release" color="primary" />
    </q-item-section>
  </q-item>
</q-list>
        </q-card-section>
        <q-card-actions class="row justify-between">
          <q-btn label="Back" class="q-ma-md bg-blue-grey-7" to="/" />
          <q-btn type="submit" label="Save" color="primary" class="q-ma-md" />
        </q-card-actions>
      </q-card>
    </q-form>
  </q-page>
</template>

<script lang="ts">
import { defineComponent, inject } from 'vue';

export default defineComponent({
  name: 'ProfilePage',
  emits: ['changedUser', 'mustLogin'],
  setup() {
    return {
      me: inject('me') as any,
    };
  },
  data() {
    const me = this.me as any;
    if (!this.me) {
      this.$emit('mustLogin');
    }
    return {
      display_name: me?.display_name,
      world_builder_name: me?.world_builder_name,
      dnd_beyond_name: me?.dnd_beyond_name,
      notify_new_adventure: me?.notify_new_adventure ?? true,
      notify_deadline: me?.notify_deadline ?? true,
      notify_release: me?.notify_release ?? true,
    };
  },
  methods: {
    async save() {
      await this.$api.patch('/api/users/' + this.me.id, {
        display_name: this.display_name,
        world_builder_name: this.world_builder_name,
        dnd_beyond_name: this.dnd_beyond_name,
        notify_new_adventure: this.notify_new_adventure,
       notify_deadline: this.notify_deadline,
        notify_release: this.notify_release,
      });
      this.$emit('changedUser');
      this.$q.notify({
        message: 'Your profile was saved!',
        type: 'positive',
      });
    },
  },
});
</script>
