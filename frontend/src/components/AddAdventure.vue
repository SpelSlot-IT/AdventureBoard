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
					<q-input v-model="title" label="Session title" autofocus />
					<q-input v-model="short_description" label="Short description" type="textarea" autogrow/>
					<q-input v-model="max_players" label="Max players" type="number" :min="1" :max="30" />
					<DatePicker v-model="start_date" label="First session" onlyWednesdays />
					<DatePicker v-model="end_date" label="Last session" onlyWednesdays />
					<q-rating v-model="rank_combat" :max="3" size="2em" icon="sym_o_swords" />
					<q-rating v-model="rank_exploration" :max="3" size="2em" icon="explore" />
					<q-rating v-model="rank_roleplaying" :max="3" size="2em" icon="theater_comedy" />
				</div>
			</q-card-section>
			<q-card-actions class="row justify-end">
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
	emits: ['eventAdded', 'canClose'],
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
			start_date: this.editExisting?.start_date || '',
			end_date: this.editExisting?.end_date || '',
			rank_combat: this.editExisting?.rank_combat || 0,
			rank_exploration: this.editExisting?.rank_exploration || 0,
			rank_roleplaying: this.editExisting?.rank_roleplaying || 0,
		};
	},
	computed: {
		filledIn() {
			return this.title != '' || this.short_description != '';
		},
	},
	methods: {
		async save() {
			const body = {
				title: this.title,
				short_description: this.short_description,
				max_players: this.max_players,
				start_date: this.start_date,
				end_date: this.end_date,
				rank_combat: this.rank_combat,
				rank_exploration: this.rank_exploration,
				rank_roleplaying: this.rank_roleplaying,
			} as any;
			if(this.editExisting) {
				body.id = this.editExisting.id;
				await this.$api.patch('/api/adventures/', body);
			} else {
				await this.$api.post('/api/adventures', body);
			}
			this.$q.notify({
				message: 'Your adventure was saved!',
				type: 'positive',
			});
			this.$emit('eventAdded');
		},
	},
	watch: {
		filledIn(v) {
			this.$emit('canClose', !v);
		},
	},
});
</script>
