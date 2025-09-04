<template>
	<q-page class="row items-center justify-evenly">
		<q-table :rows="characterArray" :columns="columns" title="Characters" hide-pagination :rows-per-page-options="[0]" wrap-cells table-class="characters">
			<template v-slot:body-cell-avatar="props">
				<q-td :props="props">
					<router-link :to="'/characters/' + props.row.id" v-if="props.value">
						<q-avatar>
							<img :src="props.value" />
						</q-avatar>
					</router-link>
				</q-td>
			</template>

			<template v-slot:body-cell-name="props">
				<q-td :props="props">
					<router-link :to="'/characters/' + props.row.id" class="text-white">
						{{props.value}}
					</router-link>
				</q-td>
			</template>
		</q-table>
	</q-page>
</template>

<style lang="scss">
	.characters td {
		max-width: 300px;
	}
</style>

<script lang="ts">
import { defineComponent, inject } from 'vue';
import { Character, fetchCharacterData } from '../util/characters';

export default defineComponent({
	name: 'CharactersPage',
	emits: ['setErrors'],
	setup() {
		return {
			me: inject('me') as any,
			columns: [
				{name: 'avatar', field: 'avatar', label: '', align: 'left', sortable: true},
				{name: 'name', field: 'name', label: 'Name', align: 'left', sortable: true},
				{name: 'player', field: 'dndbeyond_account', label: 'Player', align: 'left', sortable: true},
				{name: 'class', field: 'class_description', label: 'Class', align: 'left', sortable: true},
				{name: 'race', field: 'race', label: 'Race', align: 'left', sortable: true},
				{name: 'level', field: 'level', label: 'Level', align: 'left', sortable: true},
				{name: 'campaign', field: 'campaign', label: 'Campaign', align: 'left', sortable: true},
			],
		};
	},
	data() {
		return {
			characters: {} as {[id: number]: Character},
		};
	},
	async beforeMount() {
		try {
			this.characters = await fetchCharacterData();
		} catch(e) {
			this.$emit('setErrors', this.$extractErrors(e));
		}
	},
	methods: {
	},
	computed: {
		characterArray() {
			return Object.values(this.characters);
		},
		visibleColumns() {
			if(this.me?.privilege_level > 0) {
				return ['name', 'player', 'class', 'race', 'level', 'campaign'];
			}
			return ['name', 'player', 'class', 'race'];
		},
	},
});
</script>
