using System;
using System.Collections.Generic;
using System.Linq;

namespace Avalonia_UI.Models;

public enum WorkflowLoopRegionDraftValidationStatus
{
    Succeeded,
    LoopIdRequired,
    StartNodeRequired,
    JudgeNodeRequired,
    BoundaryNodesMustDiffer,
    BodyNodesRequired,
    BodyNodesMustBeUnique,
    BodyContainsBoundary,
    EndNodeRequired,
    UnknownNode,
    MaxIterationsInvalid,
    InputModeUnsupported,
    ContinueBranchUnsupported,
    EndBranchUnsupported,
}

public sealed record WorkflowLoopRegionDraftValidationResult
{
    public WorkflowLoopRegionDraftValidationStatus Status { get; init; }

    public string? Warning { get; init; }

    public IReadOnlyList<string> UnknownNodeIds { get; init; } = [];

    public bool Succeeded => Status == WorkflowLoopRegionDraftValidationStatus.Succeeded;

    public static WorkflowLoopRegionDraftValidationResult Validate(
        WorkflowLoopRegionDraft draft,
        IReadOnlyCollection<string> knownNodeIds)
    {
        if (string.IsNullOrWhiteSpace(draft.LoopId))
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.LoopIdRequired,
                "LOOP_REGION_ID_REQUIRED");
        }

        if (string.IsNullOrWhiteSpace(draft.StartNodeId))
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.StartNodeRequired,
                "LOOP_START_NODE_REQUIRED");
        }

        if (string.IsNullOrWhiteSpace(draft.JudgeNodeId))
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.JudgeNodeRequired,
                "LOOP_JUDGE_NODE_REQUIRED");
        }

        if (string.Equals(draft.StartNodeId, draft.JudgeNodeId, StringComparison.Ordinal))
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.BoundaryNodesMustDiffer,
                "LOOP_REGION_INVALID_BOUNDARY");
        }

        if (draft.BodyNodeIds.Count == 0)
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.BodyNodesRequired,
                "LOOP_REGION_BODY_EMPTY");
        }

        var distinctBodyIds = draft.BodyNodeIds
            .Where(nodeId => !string.IsNullOrWhiteSpace(nodeId))
            .Distinct(StringComparer.Ordinal)
            .ToArray();
        if (distinctBodyIds.Length != draft.BodyNodeIds.Count)
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.BodyNodesMustBeUnique,
                "LOOP_REGION_BODY_DUPLICATE_NODE");
        }

        if (distinctBodyIds.Contains(draft.StartNodeId, StringComparer.Ordinal) ||
            distinctBodyIds.Contains(draft.JudgeNodeId, StringComparer.Ordinal) ||
            (draft.EndNodeId is not null &&
             distinctBodyIds.Contains(draft.EndNodeId, StringComparer.Ordinal)))
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.BodyContainsBoundary,
                "LOOP_REGION_BODY_CONTAINS_BOUNDARY");
        }

        if (draft.EndNodeId is not null && string.IsNullOrWhiteSpace(draft.EndNodeId))
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.EndNodeRequired,
                "LOOP_REGION_END_NODE_REQUIRED");
        }

        var knownNodes = knownNodeIds.ToHashSet(StringComparer.Ordinal);
        var referencedNodes = new[] { draft.StartNodeId, draft.JudgeNodeId }
            .Concat(distinctBodyIds)
            .Concat(draft.EndNodeId is null ? [] : [draft.EndNodeId])
            .Distinct(StringComparer.Ordinal);
        var unknownNodes = referencedNodes
            .Where(nodeId => !knownNodes.Contains(nodeId))
            .Order(StringComparer.Ordinal)
            .ToArray();
        if (unknownNodes.Length > 0)
        {
            return new WorkflowLoopRegionDraftValidationResult
            {
                Status = WorkflowLoopRegionDraftValidationStatus.UnknownNode,
                Warning = "LOOP_REGION_UNKNOWN_NODE",
                UnknownNodeIds = unknownNodes,
            };
        }

        if (draft.MaxIterations < 1)
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.MaxIterationsInvalid,
                "LOOP_REGION_MAX_ITERATIONS_INVALID");
        }

        if (!string.Equals(
                draft.InputMode,
                WorkflowLoopRegionDraft.SupportedInputMode,
                StringComparison.Ordinal))
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.InputModeUnsupported,
                "LOOP_REGION_INPUT_MODE_UNSUPPORTED");
        }

        if (!string.Equals(
                draft.ContinueBranch,
                WorkflowLoopRegionDraft.ContinueLoopBranch,
                StringComparison.Ordinal))
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.ContinueBranchUnsupported,
                "LOOP_REGION_CONTINUE_BRANCH_UNSUPPORTED");
        }

        if (!string.Equals(
                draft.EndBranch,
                WorkflowLoopRegionDraft.EndLoopBranch,
                StringComparison.Ordinal))
        {
            return Failed(
                WorkflowLoopRegionDraftValidationStatus.EndBranchUnsupported,
                "LOOP_REGION_END_BRANCH_UNSUPPORTED");
        }

        return new WorkflowLoopRegionDraftValidationResult
        {
            Status = WorkflowLoopRegionDraftValidationStatus.Succeeded,
        };
    }

    private static WorkflowLoopRegionDraftValidationResult Failed(
        WorkflowLoopRegionDraftValidationStatus status,
        string warning)
    {
        return new WorkflowLoopRegionDraftValidationResult
        {
            Status = status,
            Warning = warning,
        };
    }
}
