<template>
  <div class="flex flex-col">
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-medium text-gray-900">Call Logs</div>
      </template>
    </LayoutHeader>
    <ListViewBuilder
      ref="listViewRef"
      :options="options"
      @row-click="openCallLog"
    />
  </div>
</template>
<script setup lang="ts">
import { LayoutHeader, ListViewBuilder } from "@/components";
import { PhoneIcon } from "@/components/icons";
import { Badge, usePageMeta } from "frappe-ui";
import { computed, h, ref } from "vue";
import LucidePhoneIncoming from "~icons/lucide/phone-incoming";
import LucidePhoneOutgoing from "~icons/lucide/phone-outgoing";

const listViewRef = ref(null);

const options = computed(() => {
  return {
    doctype: "Helpdesk Call Log",
    selectable: true,
    hideColumnSetting: false,  // Show the Columns button
    fields: [
      "name",
      "call_id",
      "telephony_medium",
      "type",
      "from_number",
      "to_number",
      "duration",
      "status",
      "caller_name",
      "ticket",
      "customer",
      "start_time",
      "end_time",
      "recording_url",
      "summary",
      "created_by_user",
      "source",
      "creation",
      "modified",
    ],
    columns: [
      {
        label: "Caller Name",
        key: "caller_name",
        width: "200px",
      },
      {
        label: "Caller Number",
        key: "from_number",
        width: "150px",
      },
      {
        label: "Called Number",
        key: "to_number",
        width: "150px",
      },
      {
        label: "Direction",
        key: "type",
        width: "120px",
        prefix: ({ row }) => {
          return h(
            row.type === "Incoming" ? LucidePhoneIncoming : LucidePhoneOutgoing,
            {
              class: "h-4 w-4",
            }
          );
        },
      },
      {
        label: "Status",
        key: "status",
        width: "120px",
        format: ({ row }) => {
          return h(Badge, {
            label: row.status || "Unknown",
            theme: getStatusTheme(row.status),
          });
        },
      },
      {
        label: "Duration",
        key: "duration",
        width: "100px",
        format: ({ row }) => {
          // Hide "0s" duration
          if (row.duration === "0s" || !row.duration) {
            return "";
          }
          return row.duration;
        },
      },
      {
        label: "Session ID",
        key: "call_id",
        width: "200px",
      },
      {
        label: "Ticket Created",
        key: "ticket",
        width: "150px",
      },
      {
        label: "Customer",
        key: "customer",
        width: "150px",
      },
      {
        label: "Telephony Medium",
        key: "telephony_medium",
        width: "150px",
      },
      {
        label: "Start Time",
        key: "start_time",
        width: "160px",
      },
      {
        label: "End Time",
        key: "end_time",
        width: "160px",
      },
      {
        label: "Recording URL",
        key: "recording_url",
        width: "200px",
      },
      {
        label: "Summary",
        key: "summary",
        width: "200px",
      },
      {
        label: "Created By",
        key: "created_by_user",
        width: "150px",
      },
      {
        label: "Source",
        key: "source",
        width: "150px",
      },
      {
        label: "Helpdesk Call Log Created",
        key: "creation",
        width: "160px",
      },
      {
        label: "Last Modified",
        key: "modified",
        width: "160px",
      },
    ],
    orderBy: "creation desc",
    emptyState: {
      title: "No Call Logs Found",
      description: "Call logs will appear here when calls are made or received",
    },
  };
});

function getStatusTheme(status: string): string {
  const themeMap: Record<string, string> = {
    Answered: "green",
    Missed: "red",
    "No Answer": "orange",
    Busy: "yellow",
    Failed: "red",
    Completed: "blue",
  };
  return themeMap[status] || "gray";
}

function openCallLog(callLogId: string): void {
  // For now, just log - can be enhanced to show call log details
  console.log("Open call log:", callLogId);
}

usePageMeta(() => {
  return {
    title: "Call Logs",
  };
});
</script>

