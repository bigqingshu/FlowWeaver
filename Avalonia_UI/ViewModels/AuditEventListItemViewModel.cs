using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class AuditEventListItemViewModel
{
    public AuditEventListItemViewModel(AuditEventDto auditEvent)
    {
        AuditEventId = auditEvent.AuditEventId;
        EventType = auditEvent.EventType;
        Decision = auditEvent.Decision;
        WorkflowRunId = auditEvent.WorkflowRunId;
        NodeRunId = auditEvent.NodeRunId;
    }

    public string AuditEventId { get; }

    public string EventType { get; }

    public string Decision { get; }

    public string? WorkflowRunId { get; }

    public string? NodeRunId { get; }

    public string WorkflowRunText =>
        string.IsNullOrWhiteSpace(WorkflowRunId) ? "-" : WorkflowRunId;

    public string NodeRunText =>
        string.IsNullOrWhiteSpace(NodeRunId) ? "-" : NodeRunId;
}
