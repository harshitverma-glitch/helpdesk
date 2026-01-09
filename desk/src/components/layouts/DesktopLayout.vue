<template>
  <div class="flex h-screen w-screen">
    <Sidebar />
    <div class="flex-1 flex flex-col h-full overflow-auto">
      <AppHeader />
      <slot />
    </div>
    <Notifications />
    <CommandPalette />
    <RingCentralCallUI ref="ringcentralCallUI" />
  </div>
</template>
<script setup>
import { Notifications, CommandPalette } from "@/components";
import AppHeader from "./AppHeader.vue";
import Sidebar from "./Sidebar.vue";
import RingCentralCallUI from "@/components/RingCentralCallUI.vue";
import { ref, provide, onMounted } from "vue";

const ringcentralCallUI = ref(null);

// Provide the RingCentral Call UI to all child components
provide("$ringcentralCallUI", ringcentralCallUI);

onMounted(() => {
  if (ringcentralCallUI.value) {
    ringcentralCallUI.value.setup();
  }
});
</script>
