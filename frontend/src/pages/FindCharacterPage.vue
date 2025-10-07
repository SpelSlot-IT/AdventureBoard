<template>
  <q-page class="row justify-evenly q-pt-lg items-start reverse">
    <q-spinner v-if="loading" size="xl" />
    <q-banner v-else-if="!dndbeyondName" class="bg-negative">D&DBeyond account unknown for this player</q-banner>
    <q-banner v-else-if="playerCharacters.length == 0" class="bg-negative">No character found for D&DBeyond account {{dndbeyondName}}</q-banner>
    <template v-else>
      <q-card class="col-11-xs col-md-6">
        <q-card-section>
          {{dndbeyondName}} has multiple characters:
          <ul>
            <li v-for="c in playerCharacters" :key="c.id">
              <router-link :to="{name: 'character', params: {id: c.id}}">
                {{c.name}}
              </router-link>
            </li>
          </ul>
        </q-card-section>
      </q-card>
    </template>
  </q-page>
</template>

<script lang="ts">
import { defineComponent, inject } from 'vue';
import { Character, fetchCharacterData } from '../util/characters';

export default defineComponent({
  name: 'FindCharacterPage',
  emits: ['setErrors'],
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      dndbeyondName: null as null | string,
      characters: null as null | {[key: number]: Character},
    };
  },
  async beforeMount() {
    try {
      this.characters = await fetchCharacterData();
    } catch (e) {
      this.$emit('setErrors', this.$extractErrors(e));
    }
  },
  computed: {
    loading() {
      return this.characters == null || this.dndbeyondName === null;
    },
    playerCharacters() {
      if(this.characters === null || !this.dndbeyondName) {
        return null;
      }
      return Object.values(this.characters).filter(c => c.dndbeyond_account.toLowerCase() == this.dndbeyondName!.toLowerCase());
    },
  },
  watch: {
    id: {
      async handler() {
        if(!/^\d+$/.test(this.id)) {
          this.dndbeyondName = this.id;
          return;
        }
        const resp = await this.$api.get('/api/users/' + this.id);
        this.dndbeyondName = resp.data.dnd_beyond_name;
      },
      immediate: true,
    },
    playerCharacters() {
      if(this.playerCharacters && this.playerCharacters.length == 1) {
        this.$router.replace({name: 'character', params: {id: this.playerCharacters[0].id}});
      }
    },
  },
});
</script>
