<template>
  <div class="flex flex-col h-full overflow-auto">
    <div class="px-6 py-4">
      <div class="text-base font-medium text-gray-900">Call Logs</div>
    </div>
    <div v-if="callLogs.data && callLogs.data.length" class="flex-1 px-6">
      <div
        v-for="callLog in callLogs.data"
        :key="callLog.name"
        class="mb-4 cursor-pointer"
        @click="openCallLog(callLog)"
      >
        <div
          class="flex flex-col gap-2 rounded-md border border-gray-200 bg-white px-3 py-2.5"
        >
          <div class="flex items-center justify-between">
            <div class="inline-flex items-center gap-2 text-base font-medium">
              <FeatherIcon
                :name="
                  callLog.type === 'Incoming'
                    ? 'phone-incoming'
                    : 'phone-outgoing'
                "
                class="h-4 w-4"
              />
              <div>
                {{
                  callLog.type === "Incoming"
                    ? __("Inbound Call")
                    : __("Outbound Call")
                }}
              </div>
            </div>
            <div class="text-sm text-gray-600">
              <Tooltip :text="dateFormat(callLog.start_time, 'MMM D, YYYY h:mm A')">
                {{ timeAgo(callLog.start_time) }}
              </Tooltip>
            </div>
          </div>

          <div class="flex items-center gap-2 text-sm text-gray-700">
            <span class="font-medium">{{ callLog.from_number }}</span>
            <FeatherIcon name="arrow-right" class="h-3 w-3" />
            <span>{{ callLog.to_number }}</span>
          </div>

          <div v-if="callLog.caller_name" class="text-sm text-gray-600">
            <span class="font-medium">Caller:</span>
            {{ callLog.caller_name }}
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <Badge
              v-if="callLog.duration && callLog.duration !== '0s'"
              :label="callLog.duration"
              theme="gray"
            >
              <template #prefix>
                <FeatherIcon name="clock" class="h-3 w-3" />
              </template>
            </Badge>
            <Badge
              :label="callLog.status || 'Unknown'"
              :theme="getStatusTheme(callLog.status)"
            />
            <Badge
              v-if="callLog.recording_url"
              label="Recording Available"
              theme="blue"
              class="cursor-pointer"
              @click.stop="toggleRecording(callLog)"
            >
              <template #prefix>
                <FeatherIcon
                  :name="
                    callLog.show_recording ? 'pause-circle' : 'play-circle'
                  "
                  class="h-3 w-3"
                />
              </template>
            </Badge>
            <Badge
              v-if="callLog.recording_url"
              label="View Transcript"
              theme="purple"
              class="cursor-pointer"
              @click.stop="openTranscriptModal(callLog)"
            >
              <template #prefix>
                <FeatherIcon name="file-text" class="h-3 w-3" />
              </template>
            </Badge>
          </div>

          <div
            v-if="callLog.show_recording && callLog.recording_url"
            class="mt-2"
            @click.stop
          >
            <CallRecordingPlayer
              :call-log-name="callLog.name"
              :recording-url="callLog.recording_url"
            />
          </div>

          <div v-if="callLog.summary" class="text-sm text-gray-600 mt-1">
            {{ callLog.summary }}
          </div>
        </div>
      </div>
    </div>
    <div
      v-else-if="!callLogs.loading"
      class="flex h-full flex-col items-center justify-center gap-3 text-gray-500"
    >
      <FeatherIcon name="phone" class="h-10 w-10" />
      <span class="text-base font-medium">No Call Logs</span>
      <span class="text-sm">Call logs for this ticket will appear here</span>
    </div>
    <div
      v-else
      class="flex h-full items-center justify-center"
    >
      <LoadingIndicator class="w-6 h-6 text-gray-600" />
    </div>

    <!-- Transcript Modal -->
    <CallTranscriptModal
      v-model="showTranscriptModal"
      :call-log-name="selectedCallLogName"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Badge, FeatherIcon, LoadingIndicator, Tooltip, createResource } from "frappe-ui";
import { timeAgo, dateFormat } from "@/utils";
import CallRecordingPlayer from "@/components/CallRecordingPlayer.vue";
import CallTranscriptModal from "@/components/CallTranscriptModal.vue";

const props = defineProps({
  ticketId: {
    type: String,
    required: true,
  },
});

const showTranscriptModal = ref(false);
const selectedCallLogName = ref("");

const callLogs = createResource({
  url: "frappe.client.get_list",
  params: {
    doctype: "Helpdesk Call Log",
    filters: {
      ticket: props.ticketId,
    },
    fields: [
      "name",
      "call_id",
      "from_number",
      "to_number",
      "type",
      "duration",
      "status",
      "caller_name",
      "start_time",
      "end_time",
      "recording_url",
      "summary",
      "creation",
    ],
    order_by: "start_time desc",
  },
  auto: true,
  transform: (data) => {
    return data.map((log) => ({
      ...log,
      show_recording: false,
    }));
  },
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

function toggleRecording(callLog: any) {
  callLog.show_recording = !callLog.show_recording;
}

function openCallLog(callLog: any) {
  // Can be enhanced to show detailed modal
  console.log("Open call log details:", callLog);
}

function openTranscriptModal(callLog: any) {
  selectedCallLogName.value = callLog.name;
  showTranscriptModal.value = true;
}
</script>

