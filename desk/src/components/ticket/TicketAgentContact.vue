<template>
  <div class="flex items-center justify-start gap-5 border-b p-5">
    <Avatar size="3xl" :image="contact.image" :label="contact.full_name || contact.name" />
    <div class="flex items-center justify-between flex-1">
      <div class="flex flex-col gap-1">
        <Tooltip :text="contact.full_name || contact.name">
          <div class="w-[242px] truncate text-2xl font-medium">
            {{ contact.full_name || contact.name }}
          </div>
        </Tooltip>
        <div v-if="ticket?.contact_mobile || contact.mobile_no" class="text-sm text-gray-600 flex items-center gap-1">
          <PhoneIcon class="h-3.5 w-3.5" />
          <span>{{ ticket?.contact_mobile || contact.mobile_no }}</span>
        </div>
        <div v-if="ticket?.contact_email || contact.email_id" class="text-sm text-gray-600 flex items-center gap-1">
          <EmailIcon class="h-3.5 w-3.5" />
          <span>{{ ticket?.contact_email || contact.email_id }}</span>
        </div>
      </div>
      <div class="flex gap-1.5">
        <Tooltip text="Make a call">
          <Button class="h-7 w-7" @click="initiateCall">
            <template #icon>
              <PhoneIcon class="h-4 w-4" />
            </template>
          </Button>
        </Tooltip>
        <Tooltip :text="contact.email_id">
          <Button class="h-7 w-7">
            <template #icon>
              <EmailIcon class="h-4 w-4" @click="openEmailBox()" />
            </template>
          </Button>
        </Tooltip>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { EmailIcon, PhoneIcon } from "@/components/icons/";
import { Avatar, Tooltip, Button, toast } from "frappe-ui";
import { inject } from "vue";

const props = defineProps({
  contact: {
    type: Object,
    required: true,
  },
  ticket: {
    type: Object,
    required: false,
    default: null,
  },
});

const emit = defineEmits(["email:open"]);

// Inject the RingCentral call UI component
const ringcentralCallUI = inject("$ringcentralCallUI", null);

function openEmailBox() {
  emit("email:open", props.contact.email_id);
}

function initiateCall() {
  // Priority: Use the phone number displayed (contact_mobile from ticket which comes from call log)
  const phoneNumber = props.ticket?.contact_mobile || props.contact.mobile_no || props.contact.phone;
  
  if (!phoneNumber) {
    toast.error("No phone number available for this contact");
    return;
  }

  if (ringcentralCallUI && ringcentralCallUI.value) {
    // Call using RingCentral with the phone number from call log (contact_mobile)
    ringcentralCallUI.value.makeOutgoingCall(phoneNumber, props.ticket?.name);
  } else {
    toast.error("RingCentral calling not available");
  }
}
</script>
