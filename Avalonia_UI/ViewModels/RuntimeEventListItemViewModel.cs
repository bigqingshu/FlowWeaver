using System;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class RuntimeEventListItemViewModel
{
    public RuntimeEventListItemViewModel(RuntimeEventDto runtimeEvent)
    {
        EventId = runtimeEvent.EventId;
        SequenceNumber = runtimeEvent.SequenceNumber;
        EventType = runtimeEvent.EventType;
        Timestamp = runtimeEvent.Timestamp;
        WorkflowRunId = runtimeEvent.WorkflowRunId;
        NodeRunId = runtimeEvent.NodeRunId;
    }

    public string EventId { get; }

    public long SequenceNumber { get; }

    public string EventType { get; }

    public DateTimeOffset Timestamp { get; }

    public string? WorkflowRunId { get; }

    public string? NodeRunId { get; }

    public string SequenceText => $"#{SequenceNumber}";

    public string TimestampText => Timestamp.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");

    public string WorkflowRunText =>
        string.IsNullOrWhiteSpace(WorkflowRunId) ? "-" : WorkflowRunId;

    public string NodeRunText =>
        string.IsNullOrWhiteSpace(NodeRunId) ? "-" : NodeRunId;
}
