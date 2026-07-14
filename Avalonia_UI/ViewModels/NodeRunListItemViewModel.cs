using System;
using System.Globalization;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class NodeRunListItemViewModel : ViewModelBase
{
    public NodeRunListItemViewModel(
        NodeRunDto nodeRun,
        DisplayTextFormatter? displayTextFormatter = null)
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
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
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

    public DisplayTextFormatter DisplayTextFormatter { get; }

    public string ProgressText =>
        Progress.HasValue
            ? string.Create(
                CultureInfo.InvariantCulture,
                $"{Math.Clamp(Progress.Value, 0.0, 1.0) * 100:0}%")
            : "-";

    public string CurrentStageText =>
        string.IsNullOrWhiteSpace(CurrentStage) ? "-" : CurrentStage;

    public string AttemptText => DisplayTextFormatter.FormatAttempt(Attempt);

    public string StatusText => DisplayTextFormatter.FormatRuntimeStatus(Status);

    public string LastHeartbeatText =>
        LastHeartbeat?.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss") ?? "-";

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(StatusText));
        OnPropertyChanged(nameof(AttemptText));
    }
}
