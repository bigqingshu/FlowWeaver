using System.Collections.Generic;

namespace Avalonia_UI.Models;

public enum WorkflowLoopRegionDraftReadStatus
{
    Succeeded,
    JsonInvalid,
    RootNotObject,
    NodesMissing,
    NodeInstanceIdRequired,
    ControlProtocolNotObject,
    ControlProtocolModeUnsupported,
    LoopRegionsNotArray,
    LoopRegionNotObject,
    DuplicateLoopId,
    OverlappingLoopNode,
    UnknownNode,
    RegionInvalid,
    EnabledModeMismatch,
}

public sealed record WorkflowLoopRegionDraftReadResult
{
    public WorkflowLoopRegionDraftReadStatus Status { get; init; }

    public string ProtocolMode { get; init; } = "preview";

    public IReadOnlyList<WorkflowLoopRegionDraft> Regions { get; init; } = [];

    public string? Warning { get; init; }

    public string? ProblemLoopId { get; init; }

    public WorkflowLoopRegionDraftValidationResult? Validation { get; init; }

    public bool Succeeded => Status == WorkflowLoopRegionDraftReadStatus.Succeeded;
}
