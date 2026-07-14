using System;
using System.Globalization;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class LoopIterationNodeListItemViewModel : ViewModelBase
{
    private readonly DisplayTextFormatter displayTextFormatter;

    public LoopIterationNodeListItemViewModel(
        LoopIterationNodeRunDto nodeRun,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        this.displayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        NodeRunId = nodeRun.NodeRunId;
        NodeInstanceId = nodeRun.NodeInstanceId;
        Role = nodeRun.Role;
        NodeType = nodeRun.NodeType;
        Status = nodeRun.Status;
        Progress = nodeRun.Progress;
        CurrentStage = nodeRun.CurrentStage;
        Attempt = nodeRun.Attempt;
    }

    public string NodeRunId { get; }

    public string NodeInstanceId { get; }

    public string Role { get; }

    public string NodeType { get; }

    public string Status { get; }

    public double? Progress { get; }

    public string? CurrentStage { get; }

    public int Attempt { get; }

    public string ProgressText => Progress.HasValue
        ? string.Create(
            CultureInfo.InvariantCulture,
            $"{Math.Clamp(Progress.Value, 0.0, 1.0) * 100:0}%")
        : "-";

    public string StatusText => displayTextFormatter.FormatRuntimeStatus(Status);

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(StatusText));
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
