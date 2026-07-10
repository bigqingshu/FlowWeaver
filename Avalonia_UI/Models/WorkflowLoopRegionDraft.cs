using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record WorkflowLoopRegionDraft
{
    public const string SupportedInputMode = "row";
    public const string ContinueLoopBranch = "continue_loop";
    public const string EndLoopBranch = "end_loop";

    public string LoopId { get; init; } = string.Empty;

    public string StartNodeId { get; init; } = string.Empty;

    public string JudgeNodeId { get; init; } = string.Empty;

    public IReadOnlyList<string> BodyNodeIds { get; init; } = [];

    public string? EndNodeId { get; init; }

    public int MaxIterations { get; init; } = 1;

    public string InputMode { get; init; } = SupportedInputMode;

    public string ContinueBranch { get; init; } = ContinueLoopBranch;

    public string EndBranch { get; init; } = EndLoopBranch;

    public bool Enabled { get; init; }
}
