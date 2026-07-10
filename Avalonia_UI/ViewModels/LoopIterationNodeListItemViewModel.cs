using System;
using System.Globalization;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class LoopIterationNodeListItemViewModel
{
    public LoopIterationNodeListItemViewModel(LoopIterationNodeRunDto nodeRun)
    {
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

    public string SourceText => string.IsNullOrWhiteSpace(SourceNodeInstanceId)
        ? "-"
        : string.IsNullOrWhiteSpace(OutputSlot)
            ? SourceNodeInstanceId
            : $"{SourceNodeInstanceId}.{OutputSlot}";
}
