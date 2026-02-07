<template>
  <q-input
    filled
    :modelValue="modelValue"
    @update:modelValue="emit"
    mask="####-##-##"
    :rules="[(v) => /^[\d]{4}-\d{2}-\d{2}$/.test(v)]"
    v-bind="$attrs"
  >
    <template v-slot:append>
      <q-icon name="event" class="cursor-pointer">
        <q-popup-proxy
          cover
          v-model="popupOpen"
          transition-show="scale"
          transition-hide="scale"
        >
          <q-date
            :modelValue="modelValue"
            @update:modelValue="emit"
            :options="isDateAllowed"
            mask="YYYY-MM-DD"
            today-btn
          >
            <div class="row items-center justify-end">
              <q-btn v-close-popup label="Close" color="primary" flat />
            </div>
          </q-date>
        </q-popup-proxy>
      </q-icon>
    </template>
  </q-input>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

const fromDateString = (dateStr: string): Date => {
  const separator = dateStr.includes('/') ? '/' : '-';
  const parts = dateStr.split(separator).map(Number);
  if (parts.length !== 3 || parts.some((p) => Number.isNaN(p))) {
    return new Date(NaN);
  }
  const [year, month, day] = parts;
  return new Date(year, month - 1, day);
};

export default defineComponent({
  name: 'DatePicker',
  emits: ['update:modelValue'],
  props: {
    modelValue: {
      type: String,
    },
    onlyWednesdays: Boolean,
  },
  data() {
    return {
      popupOpen: false,
    };
  },
  methods: {
    emit(v: string) {
      this.$emit('update:modelValue', v);
      this.popupOpen = false;
    },
    isDateAllowed(v: string): boolean {
      if (!this.onlyWednesdays) {
        return true;
      }
      const d = fromDateString(v);
      if (Number.isNaN(d.getTime())) {
        return false;
      }
      return d.getDay() % 7 == 3;
    },
  },
});
</script>
