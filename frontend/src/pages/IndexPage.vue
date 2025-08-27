<template>
  <q-page class="row items-center justify-evenly">
		<q-card v-for="a in adventures" :key="a.id">
			<q-card-section>
				<div class="text-h6">{{a.title}}</div>
				<q-chip v-for="t in a.tags.split(',')" :key="t" :label="t" color="accent" text-color="white"  />
				<div>{{a.short_description}}</div>
				<q-btn label="Details" icon="info" @click="focussed = a" color="primary" />
			</q-card-section>
		</q-card>

		<q-dialog :modelValue="!!focussed" @hide="focussed = null">
			<q-card style="min-width: 300px">
				<q-card-section>
					<div class="text-h6">{{focussed.title}}</div>
					<q-chip v-for="t in focussed.tags.split(',')" :key="t" :label="t" color="secondary" text-color="white"  />
					<div>{{focussed.short_description}}</div>
				</q-card-section>
			</q-card>
		</q-dialog>
  </q-page>
</template>

<script lang="ts">
import { defineComponent, inject } from 'vue';

export default defineComponent({
  name: 'IndexPage',
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
		};
	},
	methods: {
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
				const resp = await this.$api.get('/api/adventures?week_start=' + this.weekStart + '&week_end=' + this.weekEnd);
				this.adventures = resp.data;
			},
			immediate: true,
		},
	},
});
</script>
