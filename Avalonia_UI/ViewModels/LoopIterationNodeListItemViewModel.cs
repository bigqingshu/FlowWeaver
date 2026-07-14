using System;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class LoopIterationNodeListItemViewModel : ViewModelBase
{
    private readonly DisplayTextFormatter displayTextFormatter;
    private readonly Func<string, string> translate;

    public LoopIterationNodeListItemViewModel(
        LoopIterationNodeRunDto nodeRun,
        DisplayTextFormatter? displayTextFormatter = null,
        Func<string, string>? translate = null)
    {
        this.displayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        this.translate = translate ?? (key => key);
        NodeRunId = nodeRun.NodeRunId;
        NodeInstanceId = nodeRun.NodeInstanceId;
        Role = nodeRun.Role;
        NodeType = nodeRun.NodeType;
        Status = nodeRun.Status;
        Progress = nodeRun.Progress;
        CurrentStage = nodeRun.CurrentStage;
        Attempt = nodeRun.Attempt;
        StartedAt = nodeRun.StartedAt;
        FinishedAt = nodeRun.FinishedAt;
        Error = nodeRun.Error;
    }

    public string NodeRunId { get; }

    public string NodeInstanceId { get; }

    public string Role { get; }

    public string NodeType { get; }

    public string Status { get; }

    public double? Progress { get; }

    public string? CurrentStage { get; }

    public int Attempt { get; }

    public DateTimeOffset? StartedAt { get; }

    public DateTimeOffset? FinishedAt { get; }

    public JsonElement? Error { get; }

    public string ProgressText => Progress.HasValue
        ? string.Create(
            CultureInfo.InvariantCulture,
            $"{Math.Clamp(Progress.Value, 0.0, 1.0) * 100:0}%")
        : "-";

    public string StatusText => displayTextFormatter.FormatRuntimeStatus(Status);

    public string CurrentStageText =>
        RunDiagnosticValueFormatter.FormatOptional(CurrentStage);

    public string AttemptText => displayTextFormatter.FormatAttempt(Attempt);

    public string StartedAtText =>
        RunDiagnosticValueFormatter.FormatTimestamp(StartedAt);

    public string FinishedAtText =>
        RunDiagnosticValueFormatter.FormatTimestamp(FinishedAt);

    public string DurationText =>
        RunDiagnosticValueFormatter.FormatDuration(StartedAt, FinishedAt);

    public string NodeIdentityText => $"{NodeInstanceId} ({NodeType})";

    public string HeaderText => $"{NodeIdentityText} | {StatusText}";

    public string ErrorText => translate("runs.loop_monitor.error");

    public string DiagnosticText => string.Join(
        Environment.NewLine,
        $"{translate("runs.loop_monitor.node_run_id")}: {NodeRunId}",
        $"{translate("runs.loop_monitor.node_type")}: {NodeType}",
        $"{translate("runs.loop_monitor.role")}: {Role}",
        $"{translate("runs.loop_monitor.current_stage")}: {CurrentStageText}",
        $"{translate("runs.loop_monitor.attempt")}: {Attempt}",
        $"{translate("runs.loop_monitor.started")}: {StartedAtText}",
        $"{translate("runs.loop_monitor.finished")}: {FinishedAtText}",
        $"{translate("runs.loop_monitor.duration")}: {DurationText}");

    public string ErrorJson => RunDiagnosticValueFormatter.FormatJson(Error);

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorJson);

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(StatusText));
        OnPropertyChanged(nameof(HeaderText));
        OnPropertyChanged(nameof(AttemptText));
        OnPropertyChanged(nameof(ErrorText));
        OnPropertyChanged(nameof(DiagnosticText));
    }
}

public sealed class LoopIterationTableRefListItemViewModel
{
    public LoopIterationTableRefListItemViewModel(LoopIterationTableRefDto tableRef)
    {
        TableRefId = tableRef.TableRefId;
        Role = tableRef.Role;
        LogicalTableId = tableRef.LogicalTableId;
        StorageKind = tableRef.StorageKind;
        TableRole = tableRef.TableRole;
        Version = tableRef.Version;
        LifecycleStatus = tableRef.LifecycleStatus;
        SourceNodeInstanceId = tableRef.SourceNodeInstanceId;
        OutputSlot = tableRef.OutputSlot;
        ResultBindings = tableRef.ResultBindings;
    }

    public string TableRefId { get; }

    public string Role { get; }

    public string? LogicalTableId { get; }

    public string? StorageKind { get; }

    public string? TableRole { get; }

    public int? Version { get; }

    public string? LifecycleStatus { get; }

    public string? SourceNodeInstanceId { get; }

    public string? OutputSlot { get; }

    public ResultBindingSummaryDto[] ResultBindings { get; }

    public string SourceText
    {
        get
        {
            var logicalOutputs = ResultBindings
                .SelectMany(binding => binding.OutputSlots.Select(outputSlot =>
                    $"{binding.NodeInstanceId}.{outputSlot}"))
                .ToArray();
            if (logicalOutputs.Length > 0)
            {
                return string.Join(", ", logicalOutputs);
            }

            return string.IsNullOrWhiteSpace(SourceNodeInstanceId)
                ? "-"
                : string.IsNullOrWhiteSpace(OutputSlot)
                    ? SourceNodeInstanceId
                    : $"{SourceNodeInstanceId}.{OutputSlot}";
        }
    }
}
