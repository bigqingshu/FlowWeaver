using System;
using System.Globalization;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class NodeRunListItemViewModel
{
    public NodeRunListItemViewModel(NodeRunDto nodeRun)
    {
        NodeRunId = nodeRun.NodeRunId;
        WorkflowRunId = nodeRun.WorkflowRunId;
        NodeInstanceId = nodeRun.NodeInstanceId;
        NodeType = nodeRun.NodeType;
        Status = nodeRun.Status;
        Progress = nodeRun.Progress;
        CurrentStage = nodeRun.CurrentStage;
        Attempt = nodeRun.Attempt;
        LastHeartbeat = nodeRun.LastHeartbeat;
    }

    public string NodeRunId { get; }

    public string WorkflowRunId { get; }

    public string NodeInstanceId { get; }

    public string NodeType { get; }

    public string Status { get; }

    public double? Progress { get; }

    public string? CurrentStage { get; }

    public int Attempt { get; }

    public DateTimeOffset? LastHeartbeat { get; }

    public string ProgressText =>
        Progress.HasValue
            ? string.Create(
                CultureInfo.InvariantCulture,
                $"{Math.Clamp(Progress.Value, 0.0, 1.0) * 100:0}%")
            : "-";

    public string CurrentStageText =>
        string.IsNullOrWhiteSpace(CurrentStage) ? "-" : CurrentStage;

    public string AttemptText => $"attempt {Attempt}";

    public string LastHeartbeatText =>
        LastHeartbeat?.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss") ?? "-";
}
