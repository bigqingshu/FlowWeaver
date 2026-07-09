using System.Collections.Generic;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void AddRecentRuntimeEvent(RuntimeEventDto runtimeEvent)
    {
        AddRecentEvent(
            $"runtime_event.{runtimeEvent.SequenceNumber}",
            UiNotificationKind.Info,
            T("recent_events.source_runtime_event"),
            F(
                "format.received_runtime_event",
                runtimeEvent.EventType,
                runtimeEvent.SequenceNumber),
            FormatRecentRuntimeEventMessage(runtimeEvent));
    }

    private static string FormatRecentRuntimeEventMessage(RuntimeEventDto runtimeEvent)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(runtimeEvent.WorkflowRunId))
        {
            parts.Add($"run {runtimeEvent.WorkflowRunId}");
        }

        if (!string.IsNullOrWhiteSpace(runtimeEvent.NodeRunId))
        {
            parts.Add($"node {runtimeEvent.NodeRunId}");
        }

        return parts.Count == 0 ? string.Empty : string.Join(", ", parts);
    }
}
