using System;
using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class LoopIterationListItemViewModel : ViewModelBase
{
    private readonly DisplayTextFormatter displayTextFormatter;

    public LoopIterationListItemViewModel(
        LoopIterationRunDto iteration,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        this.displayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        LoopIterationId = iteration.LoopIterationId;
        LoopRunId = iteration.LoopRunId;
        IterationIndex = iteration.IterationIndex;
        Status = iteration.Status;
        StateVersion = iteration.StateVersion;
        InputTableRefId = iteration.InputTableRefId;
        OutputTableRefId = iteration.OutputTableRefId;
        FailedNodeRunId = iteration.FailedNodeRunId;
        StartedAt = iteration.StartedAt;
        FinishedAt = iteration.FinishedAt;
        Error = iteration.Error;
    }

    public string LoopIterationId { get; }

    public string LoopRunId { get; }

    public int IterationIndex { get; }

    public string Status { get; }

    public int StateVersion { get; }

    public string? InputTableRefId { get; }

    public string? OutputTableRefId { get; }

    public string? FailedNodeRunId { get; }

    public DateTimeOffset? StartedAt { get; }

    public DateTimeOffset? FinishedAt { get; }

    public JsonElement? Error { get; }

    public string IndexText => $"#{IterationIndex + 1}";

    public string StatusText => displayTextFormatter.FormatRuntimeStatus(Status);

    public string InputTableRefIdText =>
        RunDiagnosticValueFormatter.FormatOptional(InputTableRefId);

    public string OutputTableRefIdText =>
        RunDiagnosticValueFormatter.FormatOptional(OutputTableRefId);

    public string FailedNodeRunIdText =>
        RunDiagnosticValueFormatter.FormatOptional(FailedNodeRunId);

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
