<template>
  <q-page class="row items-center justify-evenly">
		Hello {{me.display_name}}
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
});
</script>
