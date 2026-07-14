using System;
using System.Globalization;
using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class NodeRunListItemViewModel : ViewModelBase
{
    private static readonly JsonSerializerOptions DisplayJsonOptions = new(FlowWeaverJson.Options)
    {
        WriteIndented = true,
    };

    public NodeRunListItemViewModel(
        NodeRunDto nodeRun,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        NodeRunId = nodeRun.NodeRunId;
        WorkflowRunId = nodeRun.WorkflowRunId;
        NodeInstanceId = nodeRun.NodeInstanceId;
        NodeType = nodeRun.NodeType;
        Status = nodeRun.Status;
        StateVersion = nodeRun.StateVersion;
        ExecutorId = nodeRun.ExecutorId;
        Progress = nodeRun.Progress;
        CurrentStage = nodeRun.CurrentStage;
        Attempt = nodeRun.Attempt;
        LastHeartbeat = nodeRun.LastHeartbeat;
        StartedAt = nodeRun.StartedAt;
        FinishedAt = nodeRun.FinishedAt;
        Error = nodeRun.Error;
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
    }

    public string NodeRunId { get; }

    public string WorkflowRunId { get; }

    public string NodeInstanceId { get; }

    public string NodeType { get; }

    public string Status { get; }

    public int StateVersion { get; }

    public string? ExecutorId { get; }

    public double? Progress { get; }

    public string? CurrentStage { get; }

    public int Attempt { get; }

    public DateTimeOffset? LastHeartbeat { get; }

    public DateTimeOffset? StartedAt { get; }

    public DateTimeOffset? FinishedAt { get; }

    public JsonElement? Error { get; }

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

    public string ExecutorIdText => string.IsNullOrWhiteSpace(ExecutorId) ? "-" : ExecutorId;

    public string NodeIdentityText => $"{NodeInstanceId} ({NodeType})";

    public string StartedAtText =>
        StartedAt?.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss") ?? "-";

    public string FinishedAtText =>
        FinishedAt?.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss") ?? "-";

    public string DurationText
    {
        get
        {
            if (StartedAt is null)
            {
                return "-";
            }

            var duration = (FinishedAt ?? DateTimeOffset.Now) - StartedAt.Value;
            if (duration < TimeSpan.Zero)
            {
                return "-";
            }

            return duration.TotalHours >= 1
                ? duration.ToString(@"hh\:mm\:ss", CultureInfo.CurrentCulture)
                : duration.ToString(@"mm\:ss", CultureInfo.CurrentCulture);
        }
    }

    public string ErrorJson => Error is null
        || Error.Value.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined
        ? string.Empty
        : JsonSerializer.Serialize(Error.Value, DisplayJsonOptions);

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorJson);

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(StatusText));
        OnPropertyChanged(nameof(AttemptText));
    }
}
