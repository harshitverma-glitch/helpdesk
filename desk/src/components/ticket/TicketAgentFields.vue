<template>
  <div class="flex flex-1 flex-col overflow-hidden overflow-y-auto border-b">
    <template v-for="field in fields" :key="field.fieldname">
      <!-- Special handling for contact_mobile -->
      <div
        v-if="field.fieldname === 'contact_mobile'"
        class="flex gap-2 px-6 pb-1 leading-5 first:mt-3 items-baseline"
      >
        <div class="w-[106px] shrink-0 truncate text-sm text-gray-600">
          {{ field.label }}
        </div>
        <div class="-m-0.5 min-h-[28px] flex-1 items-center overflow-hidden p-0.5 text-base">
          <input
            :value="ticket[field.fieldname]"
            @blur="(event) => update(field.fieldname, event.target.value)"
            @keyup.enter="(event) => update(field.fieldname, event.target.value)"
            class="form-control w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Enter mobile number"
            type="text"
          />
        </div>
      </div>
      
      <!-- All other fields use UniInput2 -->
      <UniInput2
        v-else
        :field="field"
        :value="ticket[field.fieldname]"
        @change="(data) => update(data.fieldname, data.value)"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { Field, FieldValue } from "@/types";
import { toast } from "frappe-ui";
import { computed } from "vue";
import UniInput2 from "../UniInput2.vue";
const emit = defineEmits(["update"]);

const props = defineProps({
  ticket: {
    type: Object,
    required: true,
  },
});

const fields = computed(() => {
  return props.ticket.fields;
});

function update(field: Field["fieldname"], value: FieldValue, event = null) {
  if (field === "subject" && value === "") {
    toast.error("Subject is required");
    event.target.value = props.ticket.subject;
    return;
  }
  
  emit("update", { field, value });
}
</script>
<style scoped>
:deep(.form-control input:not([type="checkbox"])),
:deep(.form-control select),
:deep(.form-control textarea),
:deep(.form-control button) {
  border-color: transparent;
  background: white;
}
:deep(.form-control textarea) {
  field-sizing: content;
}

:deep(.form-control button) {
  gap: 0;
}
:deep(.form-control [type="checkbox"]) {
  margin-left: 9px;
  cursor: pointer;
}

:deep(.form-control button > div) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.form-control button svg) {
  color: white;
  width: 0;
}
</style>
