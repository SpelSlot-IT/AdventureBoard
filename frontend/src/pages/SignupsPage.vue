<template>
  <q-page class="row items-center justify-evenly">
    <q-item v-for="player in users" :key="player.id" class="col-8 q-mb-md">
          <div class="text-h6">{{ player.display_name }}</div>
          <template v-if="player.signups && player.signups.length > 0">
            <div                                  >First Choice: {{ player.signups[0]?.adventure_id }} </div>
            <div v-if="player.signups.length > 1" >Second Choice: {{ player.signups[1]?.adventure_id }} </div>
            <div v-if="player.signups.length > 2" >Third Choice: {{ player.signups[2]?.adventure_id }} </div>
          </template>
          <template v-else>
            <div>No signups</div>
          </template>

    </q-item>
    <div v-if="users.length === 0" class="text-h6">No users found</div>
    <q-footer elevated>
      <div class="q-pa-md text-center">
        {{ num_signups }} users are signed up
      </div>
  </q-footer>
  </q-page>
</template>

<script lang="ts">
import { defineComponent, inject } from 'vue';
import { useRouter } from 'vue-router';

export default defineComponent({
  name: 'SignupsPage',
  emits: ['mustLogin'],
  setup(_, { emit }) {
    const me = inject<{ privilege_level: number }>('me');
    const router = useRouter();

    if (!me) {
      emit('mustLogin');
    } else if (me.privilege_level < 1) {
      router.push('/');
    }

    const users: any[] = [];

    return {
      me,
      users,
    };
  },
  async mounted() {
    const req1 = this.$api.get(
      '/api/users/full/0'
    );
    const resp = await req1;
    this.users = resp.data;
  },
  computed: {
    num_signups(): number {
      return this.users.filter((u: any) => u.signups && u.signups.length > 0).length;
    }
  },
  methods: {
  }
});
</script>
