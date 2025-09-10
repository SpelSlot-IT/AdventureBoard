<template>
  <q-page class="row justify-evenly q-pt-lg items-start reverse">
    <q-spinner v-if="loading" size="xl" />
    <q-banner v-else-if="character == null" class="bg-negative"
      >Character not found</q-banner
    >
    <template v-else>
      <img v-if="character.avatar" :src="character.avatar" class="col-3" />
      <q-card class="col-11-xs col-md-6">
        <q-card-section>
          <q-list>
            <q-item>
              <q-item-section>Name</q-item-section>
              <q-item-section>{{ character.name }}</q-item-section>
            </q-item>
            <q-separator />
            <q-item>
              <q-item-section>Character sheet</q-item-section>
              <q-item-section v-if="character.character_sheet"
                ><a :href="character.character_sheet" class="text-white">{{
                  character.character_sheet
                }}</a></q-item-section
              >
              <q-item-section v-else>not available</q-item-section>
            </q-item>
            <q-item>
              <q-item-section>Player</q-item-section>
              <q-item-section>{{ character.player_name }}</q-item-section>
            </q-item>
            <q-item v-if="me?.privilege_level > 1">
              <q-item-section>D&DBeyond account</q-item-section>
              <q-item-section>{{ character.dndbeyond_account }}</q-item-section>
            </q-item>
            <q-item>
              <q-item-section>D&DBeyond campaign</q-item-section>
              <q-item-section>{{ character.campaign }}</q-item-section>
            </q-item>
            <q-item>
              <q-item-section>Race</q-item-section>
              <q-item-section>{{ character.race }}</q-item-section>
            </q-item>
            <q-item>
              <q-item-section>Class</q-item-section>
              <q-item-section>{{ character.class_description }}</q-item-section>
            </q-item>
            <q-item>
              <q-item-section>Level</q-item-section>
              <q-item-section>{{ character.level }}</q-item-section>
            </q-item>
            <q-item>
              <q-item-section>Alignment</q-item-section>
              <q-item-section>{{ character.alignment }}</q-item-section>
            </q-item>
            <q-item v-if="character.age">
              <q-item-section>Age</q-item-section>
              <q-item-section>{{ character.age }}</q-item-section>
            </q-item>
            <q-item v-if="character.hair">
              <q-item-section>Hair</q-item-section>
              <q-item-section>{{ character.hair }}</q-item-section>
            </q-item>
            <q-item v-if="character.eyes">
              <q-item-section>Eyes</q-item-section>
              <q-item-section>{{ character.eyes }}</q-item-section>
            </q-item>
            <q-item v-if="character.skin">
              <q-item-section>Skin</q-item-section>
              <q-item-section>{{ character.skin }}</q-item-section>
            </q-item>
            <q-item v-if="character.height">
              <q-item-section>Height</q-item-section>
              <q-item-section>{{ character.height }}</q-item-section>
            </q-item>
            <q-item v-if="character.appearance">
              <q-item-section>Appearance</q-item-section>
              <q-item-section>{{ character.appearance }}</q-item-section>
            </q-item>
            <q-item v-if="character.personality_traits">
              <q-item-section>Personalitytraits</q-item-section>
              <q-item-section>{{
                character.personality_traits
              }}</q-item-section>
            </q-item>
            <q-item v-if="character.ideals">
              <q-item-section>Ideals</q-item-section>
              <q-item-section>{{ character.ideals }}</q-item-section>
            </q-item>
            <q-item v-if="character.bonds">
              <q-item-section>Bonds</q-item-section>
              <q-item-section>{{ character.bonds }}</q-item-section>
            </q-item>
            <q-item v-if="character.flaws">
              <q-item-section>Flaws</q-item-section>
              <q-item-section>{{ character.flaws }}</q-item-section>
            </q-item>
            <q-item v-if="character.appearance">
              <q-item-section>Appearance</q-item-section>
              <q-item-section>{{ character.appearance }}</q-item-section>
            </q-item>
            <q-item v-if="character.personal_possessions">
              <q-item-section>Personal possessions</q-item-section>
              <q-item-section>{{
                character.personal_possessions
              }}</q-item-section>
            </q-item>
            <q-item v-if="character.organizations">
              <q-item-section>Organizations</q-item-section>
              <q-item-section>{{ character.organizations }}</q-item-section>
            </q-item>
            <q-item v-if="character.allies">
              <q-item-section>Allies</q-item-section>
              <q-item-section>{{ character.allies }}</q-item-section>
            </q-item>
            <q-item v-if="character.enemies">
              <q-item-section>Enemies</q-item-section>
              <q-item-section>{{ character.enemies }}</q-item-section>
            </q-item>
            <q-item v-if="character.backstory">
              <q-item-section>Backstory</q-item-section>
              <q-item-section>{{ character.backstory }}</q-item-section>
            </q-item>
            <q-item v-if="character.other_notes">
              <q-item-section>Other_notes</q-item-section>
              <q-item-section>{{ character.other_notes }}</q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
    </template>
  </q-page>
</template>

<script lang="ts">
import { defineComponent, inject } from 'vue';
import { Character, fetchCharacterData } from '../util/characters';

export default defineComponent({
  name: 'CharacterPage',
  emits: ['setErrors'],
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  setup() {
    return {
      me: inject('me') as any,
    };
  },
  data() {
    return {
      characters: null as null | { [id: number]: Character },
    };
  },
  async beforeMount() {
    try {
      this.characters = await fetchCharacterData();
    } catch (e) {
      this.$emit('setErrors', this.$extractErrors(e));
    }
  },
  methods: {},
  computed: {
    loading() {
      return this.characters == null;
    },
    character() {
      return (this.characters && this.characters[+this.id]) || null;
    },
  },
});
</script>
