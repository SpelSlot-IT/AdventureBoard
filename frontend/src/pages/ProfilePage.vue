<template>
	<q-page class="row items-center justify-evenly">
		<q-form @submit="save" class="col-8">
			<q-card>
				<q-card-section class="q-gutter-lg">
					<div class="text-h6">User profile</div>
					<q-input v-model="display_name" label="Display name" />
					<q-input v-model="world_builder_name" label="World builder name" />
					<q-input v-model="dnd_beyond_name" label="D&D Beyond name" />
					<div>D&D Beyond campaign: {{ me.dnd_beyond_campaign }}</div>
				</q-card-section>
				<q-card-actions class="row justify-end">
					<q-btn type="submit" label="Save" color="primary" class="q-ma-md" />
				</q-card-actions>
			</q-card>
		</q-form>
	</q-page>
</template>

<script lang="ts">
import { defineComponent, inject } from 'vue';

export default defineComponent({
	name: 'ProfilePage',
	emits: ['changedUser'],
	setup() {
		return {
			me: inject('me') as any,
		};
	},
	data() {
		const me = this.me as any;
		return {
			display_name: me.display_name,
			world_builder_name: me.world_builder_name,
			dnd_beyond_name: me.dnd_beyond_name,
		};
	},
	methods: {
		async save() {
			await this.$api.patch('/api/users/' + this.me.id, {
				display_name: this.display_name,
				world_builder_name: this.world_builder_name,
				dnd_beyond_name: this.dnd_beyond_name,
			});
			this.$emit('changedUser');
			this.$q.notify({
				message: 'Your profile was saved!',
				type: 'positive',
			});
		},
	},
});
</script>
