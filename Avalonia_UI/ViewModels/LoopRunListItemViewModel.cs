using System;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class LoopRunListItemViewModel
{
    public LoopRunListItemViewModel(LoopRunDto loopRun)
    {
        LoopRunId = loopRun.LoopRunId;
        WorkflowRunId = loopRun.WorkflowRunId;
        LoopId = loopRun.LoopId;
        StartNodeInstanceId = loopRun.StartNodeInstanceId;
        JudgeNodeInstanceId = loopRun.JudgeNodeInstanceId;
        Status = loopRun.Status;
        CurrentIteration = loopRun.CurrentIteration;
        MaxIterations = loopRun.MaxIterations;
        ExitReason = loopRun.ExitReason;
        StartedAt = loopRun.StartedAt;
        FinishedAt = loopRun.FinishedAt;
    }

    public string LoopRunId { get; }

    public string WorkflowRunId { get; }

    public string LoopId { get; }

    public string StartNodeInstanceId { get; }

    public string JudgeNodeInstanceId { get; }

    public string Status { get; }

    public int CurrentIteration { get; }

    public int MaxIterations { get; }

    public string? ExitReason { get; }

    public DateTimeOffset? StartedAt { get; }

    public DateTimeOffset? FinishedAt { get; }

    public string ProgressText => $"{CurrentIteration}/{MaxIterations}";

    public string BoundaryText => $"{StartNodeInstanceId} -> {JudgeNodeInstanceId}";
}
