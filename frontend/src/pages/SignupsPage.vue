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
          <router-link :to="{name: 'playerCharacter', params: {id: props.row.dnd_beyond_name || 'unknown'}}" v-if="props.value">
            <q-avatar>
              <img :src="props.value" />
            </q-avatar>
          </router-link>
        </q-td>
      </template>

      <template v-slot:body-cell-name="props">
        <q-td :props="props">
          <router-link :to="{name: 'playerCharacter', params: {id: props.row.dnd_beyond_name || 'unknown'}}" class="default-text-color">
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
  emits: ['mustLogin', 'setErrors'],

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
          field: (row: any) => row.first?.adventure.title || '—',
          label: 'first Choice',
          align: 'left',
          sortable: true,
        },
        {
          name: 'second_choice',
          field: (row: any) => row.second?.adventure.title || '—',
          label: 'Second Choice',
          align: 'left',
          sortable: true,
        },
        {
          name: 'third_choice',
          field: (row: any) => row.third?.adventure.title || '—',
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
			return Object.values(this.users).map(u => {
				const ret = {
					...u,
					first: null,
					second: null,
					third: null,
				};
				for(const s of u.signups || []) {
					switch(s.priority) {
						case 1:
							ret.first = s;
							break;
						case 2:
							ret.second = s;
							break;
						case 3:
							ret.third = s;
							break;
					}
				}
				return ret;
			});
    },
    visibleColumns() {
      return ['name', 'First Choice', 'Second Choice', 'Third Choice'];
    },
  },
  methods: {
  }
});
</script>
