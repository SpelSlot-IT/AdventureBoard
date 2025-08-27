<template>
	<q-page>
		<div class="row items-center justify-evenly q-mt-md">
			<q-btn icon="chevron_left" color="primary" round @click="switchWeek(-1)" />
				Week of {{weekStart}} till {{weekEnd}}
			<q-btn icon="chevron_right" color="primary" round @click="switchWeek(1)" />
		</div>
		<q-spinner size="xl" v-if="loading" />
		<q-card v-else-if="adventures.length == 0">
			<q-card-section>
				No sessions this week yet.
			</q-card-section>
		</q-card>
		<div v-else class="row items-center justify-evenly">
			<q-card v-for="a in adventures" :key="a.id" class="col-12-xs col-4-sm q-ma-md">
				<q-card-section class="q-gutter-md">
					<q-btn v-if="me.id == a.user_id || me.privilege_level > 0" icon="edit" round color="accent" @click="editAdventure = a; addAdventure = true" class="float-right" />
					<div class="text-h6">{{a.title}}</div>
					<q-chip v-for="t in a.tags?.split(',')" :key="t" :label="t" color="accent" text-color="white"	/>
					<div>{{a.short_description}}</div>
					<div class="row justify-between">
						<q-rating v-model="a.rank_combat" :max="3" readonly size="2em" icon="sym_o_swords" />
						<q-rating v-model="a.rank_exploration" :max="3" readonly size="2em" icon="explore" />
						<q-rating v-model="a.rank_roleplaying" :max="3" readonly size="2em" icon="theater_comedy" />
					</div>
					<!-- <q-btn label="Details" icon="info" @click="focussed = a" color="primary" /> -->
				</q-card-section>
			</q-card>
		</div>

		<q-page-sticky position="bottom-right" :offset="[18, 18]">
			<q-btn fab icon="add" color="accent" @click="addAdventure = true" />
		</q-page-sticky>

		<q-dialog :modelValue="!!focussed" @hide="focussed = null">
			<q-card style="min-width: 300px">
				<q-card-section>
					<div class="text-h6">{{focussed.title}}</div>
					<q-chip v-for="t in focussed.tags?.split(',')" :key="t" :label="t" color="accent" text-color="white"	/>
					<div>{{focussed.short_description}}</div>
				</q-card-section>
			</q-card>
		</q-dialog>

		<q-dialog v-model="addAdventure" :persistent="addingAdventure">
			<div class="col-8">
				<AddAdventure @eventAdded="eventAdded" @canClose="v => addingAdventure = !v" :editExisting="editAdventure" />
			</div>
		</q-dialog>
	</q-page>
</template>

<script lang="ts">
import { defineComponent, inject } from 'vue';
import AddAdventure from '../components/AddAdventure.vue';

export default defineComponent({
	name: 'IndexPage',
	components: { AddAdventure },
	setup() {
		return {
			me: inject('me'),
		};
	},
	data() {
		let prevMonday = new Date();
		prevMonday.setDate(prevMonday.getDate() - (prevMonday.getDay() + 6) % 7);
		return {
			weekStart: prevMonday.toISOString().split('T')[0],
			adventures: [],
			focussed: null as any,
			addAdventure: false,
			addingAdventure: false,
			loading: false,
			editAdventure: null,
		};
	},
	methods: {
		async fetch() {
			try {
				this.loading = true;
				const resp = await this.$api.get('/api/adventures?week_start=' + this.weekStart + '&week_end=' + this.weekEnd);
				this.adventures = resp.data;
			} finally {
				this.loading = false;
			}
		},
		eventAdded() {
			this.addAdventure = false;
			this.fetch();
		},
		switchWeek(offset: number) {
			const d = new Date(this.weekStart);
			d.setDate(d.getDate() + offset * 7);
			this.weekStart = d.toISOString().split('T')[0];
		}
	},
	computed: {
		weekEnd() {
			const d = new Date(this.weekStart);
			d.setDate(d.getDate() + 7);
			return d.toISOString().split('T')[0];
		},
	},
	watch: {
		weekStart: {
			async handler() {
				await this.fetch();
			},
			immediate: true,
		},
	},
});
</script>
