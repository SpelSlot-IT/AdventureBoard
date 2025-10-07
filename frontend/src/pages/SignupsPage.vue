<template>
  <q-page class="row items-center justify-evenly">
    <q-table
      :rows="userArray"
      :columns="columns"
      :loading="userArray.length == 0"
      title="Signups"
      hide-pagination
      :rows-per-page-options="[0]"
      wrap-cells
      table-class="signups"
    >
      <template v-slot:body-cell-avatar="props">
        <q-td :props="props">
          <router-link :to="{name: 'playerCharacter', params: {id: props.row.id || 'TODO'}}" v-if="props.value">
            <q-avatar>
              <img :src="props.value" />
            </q-avatar>
          </router-link>
        </q-td>
      </template>

      <template v-slot:body-cell-name="props">
        <q-td :props="props">
          <router-link :to="{name: 'playerCharacter', params: {id: props.row.id || 'TODO'}}" class="default-text-color">
            {{ props.value }}
          </router-link>
        </q-td>
      </template>
    </q-table>
    <q-footer elevated>
      <div class="q-pa-md text-center">
        The number of users that have signed up for at least one adventure is: {{ num_signups }} 
      </div>
  </q-footer>
  </q-page>
</template>

<script lang="ts">
import { defineComponent, inject} from 'vue';

export default defineComponent({
  name: 'SignupsPage',
  emits: ['mustLogin'],

  data() {
    
    return {
      me: inject('me') as any,
      users: [] as any[],
      columns: [
        {
          name: 'avatar',
          field: 'avatar',
          label: '',
          align: 'left',
          sortable: false,
        },
        {
          name: 'name',
          field: 'display_name',
          label: 'Name',
          align: 'left',
          sortable: true,
        },
        {
          name: 'first_choice',
          field: (row: any) => row.signups?.[0]?.adventure.title || '—',
          label: 'first Choice',
          align: 'left',
          sortable: true,
        },
        {
          name: 'second_choice',
          field: (row: any) => row.signups?.[1]?.adventure.title || '—',
          label: 'Second Choice',
          align: 'left',
          sortable: true,
        },
        {
          name: 'third_choice',
          field: (row: any) => row.signups?.[2]?.adventure.title || '—',
          label: 'Third Choice',
          align: 'left',
          sortable: true,
        },
        {
          name: 'signup_count',
          field: (row: any) => row.signups?.length || 0,
          label: 'Num. Signups',
          align: 'left',
          sortable: true,
        },
      ],
    };
  },
  async beforeMount() {
    if (!this.me) {
      this.$emit('mustLogin');
      return;
    }
    if(this.me?.privilege_level < 1) {
      this.$emit('setErrors', ['You are not an admin']);
      return;
    }
    const resp = await this.$api.get('/api/users/signups/0');
    this.users = resp.data;
  },
  computed: {
    num_signups(): number {
      return this.users.filter((u: any) => u.signups && u.signups.length > 0).length;
    },
    userArray() {
      return Object.values(this.users);
    },
    visibleColumns() {
      return ['name', 'First Choice', 'Second Choice', 'Third Choice'];
    },
  },
  methods: {
  }
});
</script>
