<template>
  <div class="flex h-screen w-screen">
    <MobileSidebar />
    <div class="flex h-full flex-col flex-1 overflow-auto">
      <MobileAppHeader />
      <slot />
    </div>
    <RingCentralCallUI ref="ringcentralCallUI" />
  </div>
</template>
<script setup>
import MobileSidebar from "./MobileSidebar.vue";
import MobileAppHeader from "./MobileAppHeader.vue";
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
