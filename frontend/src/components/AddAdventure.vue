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
	data() {
		return {
			title: '',
			short_description: '',
			max_players: 5,
			start_date: '',
			end_date: '',
		};
	},
	computed: {
		filledIn() {
			return this.title != '' || this.short_description != '';
		},
	},
	methods: {
		async save() {
			await this.$api.post('/api/adventures', {
				title: this.title,
				short_description: this.short_description,
				max_players: this.max_players,
				start_date: this.start_date,
				end_date: this.end_date,
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
