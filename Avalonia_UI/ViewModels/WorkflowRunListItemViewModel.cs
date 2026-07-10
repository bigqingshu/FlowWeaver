using System;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class WorkflowRunListItemViewModel
{
    public WorkflowRunListItemViewModel(WorkflowRunDto run)
    {
        WorkflowRunId = run.WorkflowRunId;
        WorkflowId = run.WorkflowId;
        RevisionId = run.RevisionId;
        WorkflowVersion = run.WorkflowVersion;
        Status = run.Status;
        RunMode = run.RunMode;
        TriggerSource = run.TriggerSource;
        TargetNodeInstanceId = run.TargetNodeInstanceId;
        StartedAt = run.StartedAt;
        FinishedAt = run.FinishedAt;
        CompletionReason = run.CompletionReason;
    }

    public string WorkflowRunId { get; }

    public string WorkflowId { get; }

    public string? RevisionId { get; }

    public int WorkflowVersion { get; }

    public string Status { get; }

    public string RunMode { get; }

    public string TriggerSource { get; }

    public string? TargetNodeInstanceId { get; }

    public DateTimeOffset? StartedAt { get; }

    public DateTimeOffset? FinishedAt { get; }

    public string? CompletionReason { get; }

    public string WorkflowText => $"{WorkflowId} v{WorkflowVersion}";

    public string StartedAtText => FormatTimestamp(StartedAt);

    public string FinishedAtText => FormatTimestamp(FinishedAt);

    public string CompletionReasonText =>
        string.IsNullOrWhiteSpace(CompletionReason) ? "-" : CompletionReason;

    private static string FormatTimestamp(DateTimeOffset? value)
    {
        return value?.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss") ?? "-";
    }
}
