using System;
using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class LoopRunListItemViewModel : ViewModelBase
{
    private readonly DisplayTextFormatter displayTextFormatter;

    public LoopRunListItemViewModel(
        LoopRunDto loopRun,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        this.displayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        LoopRunId = loopRun.LoopRunId;
        WorkflowRunId = loopRun.WorkflowRunId;
        LoopId = loopRun.LoopId;
        StartNodeInstanceId = loopRun.StartNodeInstanceId;
        JudgeNodeInstanceId = loopRun.JudgeNodeInstanceId;
        Status = loopRun.Status;
        StateVersion = loopRun.StateVersion;
        CurrentIteration = loopRun.CurrentIteration;
        MaxIterations = loopRun.MaxIterations;
        ExitReason = loopRun.ExitReason;
        StartedAt = loopRun.StartedAt;
        FinishedAt = loopRun.FinishedAt;
        Error = loopRun.Error;
    }

    public string LoopRunId { get; }

    public string WorkflowRunId { get; }

    public string LoopId { get; }

    public string StartNodeInstanceId { get; }

    public string JudgeNodeInstanceId { get; }

    public string Status { get; }

    public int StateVersion { get; }

    public int CurrentIteration { get; }

    public int MaxIterations { get; }

    public string? ExitReason { get; }

    public DateTimeOffset? StartedAt { get; }

    public DateTimeOffset? FinishedAt { get; }

    public JsonElement? Error { get; }

    public string ProgressText => $"{CurrentIteration}/{MaxIterations}";

    public string StatusText => displayTextFormatter.FormatRuntimeStatus(Status);

    public string BoundaryText => $"{StartNodeInstanceId} -> {JudgeNodeInstanceId}";

    public string ExitReasonText =>
        RunDiagnosticValueFormatter.FormatOptional(ExitReason);

    public string StartedAtText =>
        RunDiagnosticValueFormatter.FormatTimestamp(StartedAt);

    public string FinishedAtText =>
        RunDiagnosticValueFormatter.FormatTimestamp(FinishedAt);

    public string DurationText =>
        RunDiagnosticValueFormatter.FormatDuration(StartedAt, FinishedAt);

    public string ErrorJson => RunDiagnosticValueFormatter.FormatJson(Error);

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorJson);

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(StatusText));
    }
}
