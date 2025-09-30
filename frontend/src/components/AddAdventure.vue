<template>
  <q-card>
    <q-form @submit="save">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">Add a new adventure</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section>
        <div class="q-gutter-lg">
          <q-input
            v-model="title"
            label="Session title"
            autofocus
            :rules="[(val) => !!val || 'Field is required']"
          />
          <q-input
            v-model="short_description"
            label="Short description"
            type="textarea"
            autogrow
            :rules="[(val) => !!val || 'Field is required']"
          />
          <q-input
            v-model="max_players"
            label="Max players"
            type="number"
            :min="1"
            :max="30"
            :rules="[(val) => !!val || 'Field is required']"
          />
          <DatePicker v-model="date" label="Date" onlyWednesdays />
          <q-input
            v-model="num_sessions"
            label="Number of sessions"
            type="number"
            :min="1"
            :max="4"
            v-if="!editExisting"
            :rules="[(val) => !!val || 'Field is required']"
          />
          <q-rating
            v-model="rank_combat"
            :max="3"
            size="2em"
            :icon="
              $q.dark.isActive
                ? 'img:/light/spiked-dragon-head.svg'
                : 'img:/dark/spiked-dragon-head.svg'
            "
          />
          <q-rating
            v-model="rank_exploration"
            :max="3"
            size="2em"
            :icon="
              $q.dark.isActive
                ? 'img:/light/dungeon-gate.svg'
                : 'img:/dark/dungeon-gate.svg'
            "
          />
          <q-rating
            v-model="rank_roleplaying"
            :max="3"
            size="2em"
            :icon="
              $q.dark.isActive
                ? 'img:/light/drama-masks.svg'
                : 'img:/dark/drama-masks.svg'
            "
          />
          <q-input
            v-if="me.privilege_level >= 2"
            v-model="requested_room"
            label="Requested room"
          />
          <q-input v-model="tags" label="Tags" type="textarea" autogrow />
        </div>
      </q-card-section>
      <q-card-actions class="row justify-end">
        <q-btn
          label="Delete"
          color="negative"
          class="q-ma-md"
          v-if="editExisting"
          @click="confirmDeletion"
        />
        <q-space />
        <q-btn type="submit" label="Save" color="primary" class="q-ma-md" />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script lang="ts">
import { defineComponent, inject } from 'vue';
import DatePicker from './DatePicker.vue';

export default defineComponent({
  name: 'AddAdventure',
  components: { DatePicker },
  emits: ['eventChange', 'canClose'],
  setup() {
    return {
      me: inject('me') as any,
    };
  },
  props: {
    editExisting: {
      type: Object,
      required: false,
    },
  },
  data() {
    return {
      title: this.editExisting?.title || '',
      short_description: this.editExisting?.short_description || '',
      max_players: this.editExisting?.max_players || 5,
      date: this.editExisting?.date || '',
      num_sessions: this.editExisting?.num_sessions || 1,
      rank_combat: this.editExisting?.rank_combat || 0,
      rank_exploration: this.editExisting?.rank_exploration || 0,
      rank_roleplaying: this.editExisting?.rank_roleplaying || 0,
      requested_room: this.editExisting?.requested_room || null,
      tags: this.editExisting?.tags || null,
    };
  },
  computed: {
    filledIn() {
      return this.title != '' || this.short_description != '';
    },
  },
  methods: {
    async save() {
      if (
        this.rank_combat == 0 &&
        this.rank_exploration == 0 &&
        this.rank_roleplaying == 0
      ) {
        this.$q.notify({
          message:
            'You must indicate how much combat, exploration and roleplaying your session will roughly have.',
          type: 'negative',
        });
        return;
      }
      const body = {
        title: this.title,
        short_description: this.short_description,
        max_players: this.max_players,
        date: this.date,
        num_sessions: this.num_sessions,
        rank_combat: this.rank_combat,
        rank_exploration: this.rank_exploration,
        rank_roleplaying: this.rank_roleplaying,
        requested_room: this.requested_room,
        tags: this.tags,
      } as any;
      if (this.editExisting) {
        await this.$api.patch('/api/adventures/' + this.editExisting.id, body);
      } else {
        await this.$api.post('/api/adventures', body);
      }
      this.$q.notify({
        message: 'Your adventure was saved!',
        type: 'positive',
      });
      this.$emit('eventChange');
    },
    confirmDeletion() {
      this.$q
        .dialog({
          title: 'Delete',
          message: `Are you sure you want to delete "${this.editExisting!.title}" on the ${this.editExisting!.date}?` +
            (this.editExisting!.signups.length > 0 
              ? `\n${this.editExisting!.signups.length} player(s) have already signed up for this adventure.` 
              : ''),
          cancel: true,
        })
        .onOk(async () => {
          await this.$api.delete('/api/adventures/' + this.editExisting!.id);
          this.$q.notify({
            message: "And.. it's gone",
            type: 'positive',
          });
          this.$emit('eventChange');
        });
    },
  },
  watch: {
    filledIn(v) {
      this.$emit('canClose', !v);
    },
  },
});
</script>
