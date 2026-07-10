using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Avalonia_UI.Models;

public static class WorkflowLoopRegionDraftReader
{
    public static WorkflowLoopRegionDraftReadResult Read(string workflowDefinitionDraftJson)
    {
        return Read(
            WorkflowDefinitionDraftSnapshot.Parse(workflowDefinitionDraftJson));
    }

    public static WorkflowLoopRegionDraftReadResult Read(
        WorkflowDefinitionDraftSnapshot snapshot)
    {
        if (!snapshot.Succeeded)
        {
            return Failed(
                WorkflowLoopRegionDraftReadStatus.JsonInvalid,
                snapshot.Warning ?? "WORKFLOW_DRAFT_JSON_INVALID");
        }

        var root = snapshot.Root;
        if (root.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                WorkflowLoopRegionDraftReadStatus.RootNotObject,
                "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
        }

        if (!root.TryGetProperty("nodes", out var nodes) ||
            nodes.ValueKind != JsonValueKind.Array)
        {
            return Failed(
                WorkflowLoopRegionDraftReadStatus.NodesMissing,
                "WORKFLOW_DRAFT_NODES_MISSING");
        }

        var knownNodeIds = ReadNodeIds(nodes);
        if (knownNodeIds is null)
        {
            return Failed(
                WorkflowLoopRegionDraftReadStatus.NodeInstanceIdRequired,
                "NODE_INSTANCE_ID_REQUIRED");
        }

        if (!root.TryGetProperty("control_protocol", out var controlProtocol))
        {
            return Succeeded("preview", []);
        }

        if (controlProtocol.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                WorkflowLoopRegionDraftReadStatus.ControlProtocolNotObject,
                "CONTROL_PROTOCOL_NOT_OBJECT");
        }

        var protocolMode = ReadString(controlProtocol, "mode", "preview");
        if (protocolMode is not ("preview" or "enabled"))
        {
            return Failed(
                WorkflowLoopRegionDraftReadStatus.ControlProtocolModeUnsupported,
                "CONTROL_PROTOCOL_MODE_UNSUPPORTED");
        }

        if (!controlProtocol.TryGetProperty("loop_regions", out var loopRegions))
        {
            return Succeeded(protocolMode, []);
        }

        if (loopRegions.ValueKind != JsonValueKind.Array)
        {
            return Failed(
                WorkflowLoopRegionDraftReadStatus.LoopRegionsNotArray,
                "LOOP_REGIONS_NOT_ARRAY");
        }

        var result = new List<WorkflowLoopRegionDraft>();
        var loopIds = new HashSet<string>(StringComparer.Ordinal);
        var assignedNodes = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var regionElement in loopRegions.EnumerateArray())
        {
            if (regionElement.ValueKind != JsonValueKind.Object)
            {
                return Failed(
                    WorkflowLoopRegionDraftReadStatus.LoopRegionNotObject,
                    "LOOP_REGION_NOT_OBJECT");
            }

            var bodyRead = ReadStringArray(regionElement, "body_node_ids");
            if (!bodyRead.Succeeded)
            {
                return Failed(
                    WorkflowLoopRegionDraftReadStatus.RegionInvalid,
                    bodyRead.Warning);
            }

            if (!TryReadMaxIterations(regionElement, out var maxIterations))
            {
                return Failed(
                    WorkflowLoopRegionDraftReadStatus.RegionInvalid,
                    "LOOP_REGION_MAX_ITERATIONS_INVALID");
            }

            var draft = new WorkflowLoopRegionDraft
            {
                LoopId = ReadString(regionElement, "loop_id"),
                StartNodeId = ReadString(regionElement, "start_node_id"),
                JudgeNodeId = ReadString(regionElement, "judge_node_id"),
                BodyNodeIds = bodyRead.Values,
                EndNodeId = ReadOptionalString(regionElement, "end_node_id"),
                MaxIterations = maxIterations,
                InputMode = ReadString(
                    regionElement,
                    "input_mode",
                    WorkflowLoopRegionDraft.SupportedInputMode),
                ContinueBranch = ReadString(
                    regionElement,
                    "continue_branch",
                    WorkflowLoopRegionDraft.ContinueLoopBranch),
                EndBranch = ReadString(
                    regionElement,
                    "end_branch",
                    WorkflowLoopRegionDraft.EndLoopBranch),
                Enabled = ReadBool(regionElement, "enabled"),
            };

            if (!loopIds.Add(draft.LoopId))
            {
                return Failed(
                    WorkflowLoopRegionDraftReadStatus.DuplicateLoopId,
                    "DUPLICATE_LOOP_REGION_ID",
                    draft.LoopId);
            }

            var validation = WorkflowLoopRegionDraftValidationResult.Validate(
                draft,
                knownNodeIds);
            if (!validation.Succeeded)
            {
                return new WorkflowLoopRegionDraftReadResult
                {
                    Status = validation.Status == WorkflowLoopRegionDraftValidationStatus.UnknownNode
                        ? WorkflowLoopRegionDraftReadStatus.UnknownNode
                        : WorkflowLoopRegionDraftReadStatus.RegionInvalid,
                    ProtocolMode = protocolMode,
                    Regions = result,
                    Warning = validation.Warning,
                    ProblemLoopId = draft.LoopId,
                    Validation = validation,
                };
            }

            if (draft.Enabled && protocolMode != "enabled")
            {
                return new WorkflowLoopRegionDraftReadResult
                {
                    Status = WorkflowLoopRegionDraftReadStatus.EnabledModeMismatch,
                    ProtocolMode = protocolMode,
                    Regions = result,
                    Warning = "LOOP_REGION_ENABLED_REQUIRES_CONTROL_PROTOCOL",
                    ProblemLoopId = draft.LoopId,
                };
            }

            foreach (var nodeId in RegionNodeIds(draft).Distinct(StringComparer.Ordinal))
            {
                if (assignedNodes.ContainsKey(nodeId))
                {
                    return new WorkflowLoopRegionDraftReadResult
                    {
                        Status = WorkflowLoopRegionDraftReadStatus.OverlappingLoopNode,
                        ProtocolMode = protocolMode,
                        Regions = result,
                        Warning = "NESTED_LOOP_REGION_UNAVAILABLE",
                        ProblemLoopId = draft.LoopId,
                    };
                }

                assignedNodes[nodeId] = draft.LoopId;
            }

            result.Add(draft);
        }

        return Succeeded(protocolMode, result);
    }

    private static IReadOnlyList<string>? ReadNodeIds(JsonElement nodes)
    {
        var result = new List<string>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var node in nodes.EnumerateArray())
        {
            if (node.ValueKind != JsonValueKind.Object)
            {
                return null;
            }

            var nodeId = ReadString(node, "node_instance_id");
            if (string.IsNullOrWhiteSpace(nodeId) || !seen.Add(nodeId))
            {
                return null;
            }

            result.Add(nodeId);
        }

        return result;
    }

    private static IEnumerable<string> RegionNodeIds(WorkflowLoopRegionDraft draft)
    {
        return new[] { draft.StartNodeId, draft.JudgeNodeId }
            .Concat(draft.BodyNodeIds)
            .Concat(draft.EndNodeId is null ? [] : [draft.EndNodeId]);
    }

    private static StringArrayRead ReadStringArray(
        JsonElement element,
        string propertyName)
    {
        if (!element.TryGetProperty(propertyName, out var value) ||
            value.ValueKind != JsonValueKind.Array)
        {
            return new StringArrayRead(false, [], "LOOP_REGION_BODY_NOT_ARRAY");
        }

        var result = new List<string>();
        foreach (var item in value.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.String)
            {
                return new StringArrayRead(false, [], "LOOP_REGION_BODY_NODE_INVALID");
            }

            result.Add(item.GetString() ?? string.Empty);
        }

        return new StringArrayRead(true, result, string.Empty);
    }

    private static bool TryReadMaxIterations(JsonElement element, out int value)
    {
        if (!element.TryGetProperty("max_iterations", out var property))
        {
            value = 1;
            return true;
        }

        value = 0;
        return property.ValueKind == JsonValueKind.Number &&
            property.TryGetInt32(out value) &&
            value >= 1;
    }

    private static string ReadString(
        JsonElement element,
        string propertyName,
        string defaultValue = "")
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.String
                ? property.GetString() ?? defaultValue
                : defaultValue;
    }

    private static string? ReadOptionalString(JsonElement element, string propertyName)
    {
        if (!element.TryGetProperty(propertyName, out var property) ||
            property.ValueKind == JsonValueKind.Null)
        {
            return null;
        }

        return property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : string.Empty;
    }

    private static bool ReadBool(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind is JsonValueKind.True or JsonValueKind.False &&
            property.GetBoolean();
    }

    private static WorkflowLoopRegionDraftReadResult Succeeded(
        string protocolMode,
        IReadOnlyList<WorkflowLoopRegionDraft> regions)
    {
        return new WorkflowLoopRegionDraftReadResult
        {
            Status = WorkflowLoopRegionDraftReadStatus.Succeeded,
            ProtocolMode = protocolMode,
            Regions = regions,
        };
    }

    private static WorkflowLoopRegionDraftReadResult Failed(
        WorkflowLoopRegionDraftReadStatus status,
        string warning,
        string? problemLoopId = null)
    {
        return new WorkflowLoopRegionDraftReadResult
        {
            Status = status,
            Warning = warning,
            ProblemLoopId = problemLoopId,
        };
    }

    private sealed record StringArrayRead(
        bool Succeeded,
        IReadOnlyList<string> Values,
        string Warning);
}
