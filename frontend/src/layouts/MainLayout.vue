<template>
	<q-layout view="lHh Lpr lFf">
		<q-header elevated>
			<q-toolbar class="row justify-between">
				<q-btn stretch flat label="Spelslot" to="/" />
				<div v-if="version">v{{version}}</div>
				<div v-if="me">
					<q-btn :icon="me.profile_pic ? 'img:' + me.profile_pic : 'settings'" rounded>
						<q-menu>
							<q-list style="min-width: 100px">
								<q-item to="/profile">
									<q-item-section>Edit profile</q-item-section>
								</q-item>
								<q-item clickable v-close-popup @click="logout">
									<q-item-section>Log out</q-item-section>
								</q-item>
								<q-item clickable v-close-popup v-if="me.privilege_level > 0">
									<q-item-section>Admin fancy</q-item-section>
								</q-item>
							</q-list>
						</q-menu>
					</q-btn>
				</div>
			</q-toolbar>
		</q-header>

		<q-page-container>
			<q-page v-if="!me" class="row items-center justify-evenly">
				<div>
					<q-spinner size="xl" />
						Logging you in...
				</div>
			</q-page>
			<q-page v-else-if="errors.length > 0" class="q-px-lg q-pt-md">
				<q-banner v-for="e in errors" :key="e" class="bg-negative" rounded>{{e}}</q-banner>
			</q-page>
			<q-page v-else-if="loading" class="q-px-lg q-pt-md">
				<q-spinner size="xl" />
			</q-page>
			<router-view v-else @setErrors="es => errors = es" @changedUser="changedUser" />
		</q-page-container>
	</q-layout>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';

export default defineComponent({
	name: 'MainLayout',

	data() {
		return {
			loading: false,
			errors: [] as string[],
			version: '',
			me: null as null | {
				id: number;
				display_name: string;
				world_builder_name: string;
				dnd_beyond_name: string;
				dnd_beyond_campaign: number;
				privilege_level: number;
				profile_pic: string;
			}
		}
	},

	methods: {
		async changedUser() {
			this.me = (await this.$api.get('/api/users/me')).data;
		},
		logout() {
			location.href = '/api/logout';
		},
	},

	async beforeMount() {
		const aliveReq = this.$api.get('/api/alive');
		const meReq = this.$api.get('/api/users/me');
		const aliveResp = await aliveReq;
		if(aliveResp.data.status != 'ok') {
			this.errors = ['Service is unavailable'];
		}
		this.version = aliveResp.data.version;
		const meResp = await meReq;
		this.me = meResp.data;
	},

	provide() {
		return {
			me: computed(() => this.me),
		}
	},

	computed: {
		notLoggedInError() {
			// I've added this indirection because watching this Ref direct didn't seem to work.
			return this.$notLoggedInError.value;
		},
	},

	watch: {
		notLoggedInError(nv: boolean) { // This is set to true by boot/errorhandler.ts to indicate an RPC received a HTTP 401. Handle it and clear it.
			if(nv) {
				location.href = '/api/login';
				this.$notLoggedInError.value = false;
			}
		},
		'$route.fullPath'() {
			this.errors = [];
		},
	},
});
</script>
