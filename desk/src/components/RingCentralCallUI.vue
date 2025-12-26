<template>
  <div v-show="showCallPopup" v-bind="$attrs">
    <div
      ref="callPopup"
      class="fixed z-20 flex w-60 cursor-move select-none flex-col rounded-lg bg-white border border-gray-300 p-4 shadow-2xl"
      :style="style"
    >
      <div class="flex flex-row-reverse items-center gap-1">
        <FeatherIcon
          name="x"
          class="h-4 w-4 cursor-pointer text-gray-600 hover:text-gray-800"
          @click="closeCallWindow"
        />
      </div>
      <div class="flex flex-col items-center justify-center gap-3">
        <Avatar
          v-if="contact?.image"
          :image="contact.image"
          :label="contact.full_name"
          size="3xl"
          class="!h-24 !w-24"
        />
        <Avatar
          v-else
          :label="contact?.full_name ?? 'Unknown'"
          size="3xl"
          class="!h-24 !w-24"
        />
        <div class="flex flex-col items-center justify-center gap-1">
          <div class="text-xl font-medium text-gray-900">
            {{ contact?.full_name ?? __('Unknown') }}
          </div>
          <div class="text-sm text-gray-600">{{ contact?.mobile_no }}</div>
        </div>
        <div class="my-1 text-base text-gray-700">
          {{ __('Opening RingCentral...') }}
        </div>
        <div class="flex gap-2">
          <Button
            variant="solid"
            :label="__('Call')"
            @click="makeRingCentralCall"
          >
            <template #prefix>
              <FeatherIcon name="phone" class="h-4 w-4" />
            </template>
          </Button>
          <Button
            :label="__('Cancel')"
            @click="closeCallWindow"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Avatar, Button, FeatherIcon, call, toast } from "frappe-ui";
import { ref, computed } from "vue";
import { useDraggable } from "@vueuse/core";

const callPopup = ref();
const showCallPopup = ref(false);
const contact = ref<any>({});
const mobileNumber = ref("");
const ticketId = ref<string | null>(null);

const { x, y } = useDraggable(callPopup, {
  initialValue: { x: 10, y: window.innerHeight - 350 },
});

const style = computed(() => {
  return {
    top: y.value + "px",
    left: x.value + "px",
  };
});

function setup() {
  // RingCentral doesn't need special setup like Twilio SDK
  console.log("RingCentral call button ready for Helpdesk");
}

async function makeOutgoingCall(number: string, ticket?: string) {
  if (!number) {
    toast.error("No phone number provided");
    return;
  }

  mobileNumber.value = number;
  ticketId.value = ticket || null;

  // Try to fetch contact details
  try {
    const response = await call("helpdesk.api.ringcentral_calling.get_contact_by_phone", {
      number: number,
    });
    if (response) {
      contact.value = response;
    } else {
      contact.value = {
        full_name: "Unknown",
        mobile_no: number,
      };
    }
  } catch (error) {
    contact.value = {
      full_name: "Unknown",
      mobile_no: number,
    };
  }

  showCallPopup.value = true;

  // Auto-trigger call after a short delay
  setTimeout(() => {
    makeRingCentralCall();
  }, 500);
}

function makeRingCentralCall() {
  if (!mobileNumber.value) {
    toast.error("No phone number provided");
    return;
  }

  // Create a Helpdesk Call Log
  createCallLog(mobileNumber.value);

  // Try RingCentral app first (rcapp:// protocol)
  // If app not installed, fallback to web interface
  const appUrl = `rcapp://r/call?number=${encodeURIComponent(mobileNumber.value)}`;
  const webUrl = `https://app.ringcentral.com/app/dialer?number=${encodeURIComponent(mobileNumber.value)}`;

  // Attempt to open app
  const iframe = document.createElement("iframe");
  iframe.style.display = "none";
  iframe.src = appUrl;
  document.body.appendChild(iframe);

  // Fallback to web after short delay if app doesn't open
  setTimeout(() => {
    window.open(webUrl, "_blank");
    document.body.removeChild(iframe);
  }, 1000);

  toast.success(`Opening RingCentral to call ${mobileNumber.value}`);

  // Close popup after initiating call
  setTimeout(() => {
    closeCallWindow();
  }, 1500);
}

async function createCallLog(number: string) {
  try {
    await call("helpdesk.api.ringcentral_calling.create_manual_call_log", {
      phone_number: number,
      contact_name: contact.value.full_name || "Unknown",
      ticket_id: ticketId.value,
    });
  } catch (error) {
    console.error("Error creating call log:", error);
    // Don't show error to user - call should still proceed
  }
}

function closeCallWindow() {
  showCallPopup.value = false;
  contact.value = {};
  mobileNumber.value = "";
  ticketId.value = null;
}

defineExpose({
  setup,
  makeOutgoingCall,
});
</script>

<style scoped>
/* Pulse animation for avatar */
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>

