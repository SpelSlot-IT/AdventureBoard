<template>
  <q-page class="q-pa-lg" style="max-width: 800px; margin: auto">
    <div class="text-h5 q-mb-md">Instant Mode Ranges</div>
    <p class="text-body2 text-grey-7 q-mb-lg">
      Sessions whose date falls within one of these ranges use <strong>instant signup</strong>:
      one button, first-come first-served, assignments visible immediately.
      Sessions outside these ranges use the normal karma-based flow.
    </p>

    <!-- Existing ranges -->
    <q-card class="q-mb-lg">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Active ranges</div>
        <q-list separator v-if="ranges.length > 0">
          <q-item v-for="r in ranges" :key="r.id" class="items-center">
            <q-item-section>
              <q-item-label>{{ r.label || '(no label)' }}</q-item-label>
              <q-item-label caption>{{ describeRange(r) }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                round
                icon="delete"
                color="negative"
                size="sm"
                :loading="deleting === r.id"
                @click="deleteRange(r.id)"
              />
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else class="text-grey-6 q-py-sm">No ranges configured yet.</div>
      </q-card-section>
    </q-card>

    <!-- Add new range -->
    <q-card>
      <q-card-section>
        <div class="text-h6 q-mb-md">Add range</div>

        <q-tabs v-model="tab" dense class="q-mb-md" align="left">
          <q-tab name="one-time" label="One-time date range" />
          <q-tab name="recurring" label="Recurring (Nth weekday)" />
        </q-tabs>

        <q-form @submit.prevent="submit" class="q-gutter-md">
          <q-input
            v-model="form.label"
            label="Label (optional)"
            outlined
            dense
            hint="e.g. Summer Break 2026"
          />

          <template v-if="tab === 'one-time'">
            <div class="row q-gutter-md">
              <q-input
                v-model="form.start_date"
                label="Start date"
                type="date"
                outlined
                dense
                class="col"
                :rules="[v => !!v || 'Required']"
              />
              <q-input
                v-model="form.end_date"
                label="End date"
                type="date"
                outlined
                dense
                class="col"
                :rules="[v => !!v || 'Required']"
              />
            </div>
          </template>

          <template v-else>
            <div class="row q-gutter-md">
              <q-select
                v-model="form.recurrence_week_of_month"
                :options="weekOptions"
                label="Which week"
                outlined
                dense
                class="col"
                emit-value
                map-options
                :rules="[v => v !== null || 'Required']"
              />
              <q-select
                v-model="form.recurrence_weekday"
                :options="dayOptions"
                label="Day of week"
                outlined
                dense
                class="col"
                emit-value
                map-options
                :rules="[v => v !== null || 'Required']"
              />
            </div>
            <div class="text-caption text-grey-7" v-if="recurringPreview">
              Matches: {{ recurringPreview }}
            </div>
          </template>

          <div>
            <q-btn
              type="submit"
              label="Add range"
              color="primary"
              icon="add"
              :loading="saving"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

interface InstantModeRange {
  id: number;
  label: string | null;
  start_date: string | null;
  end_date: string | null;
  is_recurring: boolean;
  recurrence_weekday: number | null;
  recurrence_week_of_month: number | null;
}

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const ORDINALS = ['', '1st', '2nd', '3rd', '4th', '5th'];

export default defineComponent({
  name: 'InstantModePage',
  data() {
    return {
      ranges: [] as InstantModeRange[],
      tab: 'one-time' as 'one-time' | 'recurring',
      saving: false,
      deleting: null as number | null,
      form: {
        label: '',
        start_date: '',
        end_date: '',
        recurrence_weekday: null as number | null,
        recurrence_week_of_month: null as number | null,
      },
      dayOptions: DAY_NAMES.map((label, value) => ({ label, value })),
      weekOptions: [1, 2, 3, 4, 5].map((n) => ({
        label: `${ORDINALS[n]} week`,
        value: n,
      })),
    };
  },
  computed: {
    recurringPreview(): string {
      const { recurrence_weekday: d, recurrence_week_of_month: w } = this.form;
      if (d === null || w === null) return '';
      return `every ${ORDINALS[w]} ${DAY_NAMES[d]} of each month`;
    },
  },
  methods: {
    describeRange(r: InstantModeRange): string {
      if (r.is_recurring) {
        const day = r.recurrence_weekday !== null ? DAY_NAMES[r.recurrence_weekday] : '?';
        const week = r.recurrence_week_of_month !== null ? ORDINALS[r.recurrence_week_of_month] : '?';
        return `Recurring: every ${week} ${day} of each month`;
      }
      return `${r.start_date} → ${r.end_date}`;
    },
    async fetchRanges() {
      const resp = await this.$api.get('/api/instant-mode-ranges');
      this.ranges = resp.data;
    },
    async submit() {
      this.saving = true;
      try {
        const payload: Record<string, unknown> = { label: this.form.label || null };
        if (this.tab === 'one-time') {
          payload.is_recurring = false;
          payload.start_date = this.form.start_date;
          payload.end_date = this.form.end_date;
        } else {
          payload.is_recurring = true;
          payload.recurrence_weekday = this.form.recurrence_weekday;
          payload.recurrence_week_of_month = this.form.recurrence_week_of_month;
        }
        await this.$api.post('/api/instant-mode-ranges', payload);
        this.$q.notify({ message: 'Range added', type: 'positive' });
        this.form = { label: '', start_date: '', end_date: '', recurrence_weekday: null, recurrence_week_of_month: null };
        await this.fetchRanges();
      } catch (e) {
        this.$q.notify({ message: 'Failed to add range', type: 'negative' });
      } finally {
        this.saving = false;
      }
    },
    async deleteRange(id: number) {
      this.deleting = id;
      try {
        await this.$api.delete(`/api/instant-mode-ranges/${id}`);
        this.$q.notify({ message: 'Range removed', type: 'positive' });
        await this.fetchRanges();
      } catch (e) {
        this.$q.notify({ message: 'Failed to remove range', type: 'negative' });
      } finally {
        this.deleting = null;
      }
    },
  },
  mounted() {
    this.fetchRanges();
  },
});
</script>
