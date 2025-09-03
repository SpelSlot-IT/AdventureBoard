<template>
  <router-view />
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { IconSet } from 'quasar';

const myIcons = {
  'app:icon1': 'img:/quasar-logo-vertical.svg',
  'app:icon2': 'img:/icon2.svg',
  'app:copy': 'fas fa-copy',
};

IconSet.iconMapFn = (iconName) => {
  const icon = myIcons[iconName];
  if (icon !== undefined) {
    return { icon };
  }
};

export default defineComponent({
  name: 'App',
});
</script>
