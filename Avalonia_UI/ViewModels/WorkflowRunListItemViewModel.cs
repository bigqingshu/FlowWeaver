using System;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class WorkflowRunListItemViewModel : ViewModelBase
{
    private readonly Func<string, string> translate;
    private readonly DisplayTextFormatter displayTextFormatter;

    public WorkflowRunListItemViewModel(
        WorkflowRunDto run,
        Func<string, string>? translate = null,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        this.translate = translate ?? DefaultText;
        this.displayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
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

    public string StatusText => displayTextFormatter.FormatRuntimeStatus(Status);

    public string RunModeText =>
        $"{translate($"runs.mode.{RunMode}")} ({RunMode})";

    public string TriggerSourceText =>
        $"{translate($"runs.trigger.{TriggerSource}")} ({TriggerSource})";

    public bool IsTerminal => Status is
        "SUCCEEDED" or "FAILED" or "CANCELLED" or "ABORTED";

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(StatusText));
        OnPropertyChanged(nameof(RunModeText));
        OnPropertyChanged(nameof(TriggerSourceText));
    }

    private static string FormatTimestamp(DateTimeOffset? value)
    {
        return value?.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss") ?? "-";
    }

    private static string DefaultText(string key)
    {
        return key switch
        {
            "runs.mode.full" => "Full run",
            "runs.mode.preview_to_node" => "Preview to node",
            "runs.trigger.manual" => "Manual",
            "runs.trigger.background_manual" => "Background manual",
            _ => key,
        };
    }
}
