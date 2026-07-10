using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Avalonia_UI.Models;

public enum WorkflowLoopRegionDraftPatchStatus
{
    Succeeded,
    JsonInvalid,
    RootNotObject,
    NodesMissing,
    NodeInstanceIdRequired,
    ControlProtocolNotObject,
    LoopRegionsNotArray,
    LoopRegionNotObject,
    DuplicateLoopId,
    LoopRegionNotFound,
    NodeConfigNotObject,
    ValidationFailed,
}

public sealed record WorkflowLoopRegionDraftPatchResult
{
    public WorkflowLoopRegionDraftPatchStatus Status { get; init; }

    public string UpdatedWorkflowDefinitionDraftJson { get; init; } = string.Empty;

    public string? Warning { get; init; }

    public WorkflowLoopRegionDraftValidationResult? Validation { get; init; }

    public bool Succeeded => Status == WorkflowLoopRegionDraftPatchStatus.Succeeded;
}

public static class WorkflowLoopRegionDraftPatcher
{
    private static readonly JsonSerializerOptions IndentedJsonOptions = new()
    {
        WriteIndented = true,
    };

    public static WorkflowLoopRegionDraftPatchResult Upsert(
        string workflowDefinitionDraftJson,
        WorkflowLoopRegionDraft draft,
        string? existingLoopId = null)
    {
        var document = ReadDocument(workflowDefinitionDraftJson);
        if (!document.Succeeded)
        {
            return document.Failure!;
        }

        var validation = WorkflowLoopRegionDraftValidationResult.Validate(
            draft,
            document.Nodes!.Keys.ToArray());
        if (!validation.Succeeded)
        {
            return new WorkflowLoopRegionDraftPatchResult
            {
                Status = WorkflowLoopRegionDraftPatchStatus.ValidationFailed,
                Warning = validation.Warning,
                Validation = validation,
            };
        }

        var protocolRead = GetOrCreateProtocol(document.Root!);
        if (!protocolRead.Succeeded)
        {
            return protocolRead.Failure!;
        }

        var regionsRead = GetOrCreateLoopRegions(protocolRead.Protocol!);
        if (!regionsRead.Succeeded)
        {
            return regionsRead.Failure!;
        }

        var loopRegions = regionsRead.Regions!;
        var lookupLoopId = string.IsNullOrWhiteSpace(existingLoopId)
            ? draft.LoopId
            : existingLoopId;
        var targetIndex = -1;
        JsonObject? targetRegion = null;
        var draftNodeIds = RegionNodeIds(draft).ToHashSet(StringComparer.Ordinal);
        for (var index = 0; index < loopRegions.Count; index++)
        {
            if (loopRegions[index] is not JsonObject region)
            {
                return Failed(
                    WorkflowLoopRegionDraftPatchStatus.LoopRegionNotObject,
                    "LOOP_REGION_NOT_OBJECT");
            }

            var loopId = GetString(region, "loop_id");
            if (string.IsNullOrWhiteSpace(loopId))
            {
                return Failed(
                    WorkflowLoopRegionDraftPatchStatus.ValidationFailed,
                    "LOOP_REGION_ID_REQUIRED");
            }

            if (string.Equals(loopId, lookupLoopId, StringComparison.Ordinal))
            {
                targetIndex = index;
                targetRegion = region;
                continue;
            }

            if (string.Equals(loopId, draft.LoopId, StringComparison.Ordinal))
            {
                return Failed(
                    WorkflowLoopRegionDraftPatchStatus.DuplicateLoopId,
                    "DUPLICATE_LOOP_REGION_ID");
            }

            var overlappingNodes = ReadRegionNodeIds(region)
                .Where(draftNodeIds.Contains)
                .Order(StringComparer.Ordinal)
                .ToArray();
            if (overlappingNodes.Length > 0)
            {
                return Failed(
                    WorkflowLoopRegionDraftPatchStatus.ValidationFailed,
                    "NESTED_LOOP_REGION_UNAVAILABLE");
            }
        }

        if (!string.IsNullOrWhiteSpace(existingLoopId) && targetRegion is null)
        {
            return Failed(
                WorkflowLoopRegionDraftPatchStatus.LoopRegionNotFound,
                "LOOP_REGION_NOT_FOUND");
        }

        var oldLoopId = targetRegion is null
            ? null
            : GetString(targetRegion, "loop_id");
        var oldStartNodeId = targetRegion is null
            ? null
            : GetString(targetRegion, "start_node_id");
        var oldJudgeNodeId = targetRegion is null
            ? null
            : GetString(targetRegion, "judge_node_id");

        targetRegion ??= new JsonObject();
        ApplyDraft(targetRegion, draft);
        if (targetIndex < 0)
        {
            loopRegions.Add(targetRegion);
        }

        var syncFailure = SynchronizeNodeLoopIds(
            document.Nodes!,
            oldLoopId,
            oldStartNodeId,
            oldJudgeNodeId,
            draft);
        if (syncFailure is not null)
        {
            return syncFailure;
        }

        NormalizeProtocol(protocolRead.Protocol!, loopRegions);
        return Succeeded(document.Root!);
    }

    public static WorkflowLoopRegionDraftPatchResult Delete(
        string workflowDefinitionDraftJson,
        string loopId)
    {
        if (string.IsNullOrWhiteSpace(loopId))
        {
            return Failed(
                WorkflowLoopRegionDraftPatchStatus.ValidationFailed,
                "LOOP_REGION_ID_REQUIRED");
        }

        var document = ReadDocument(workflowDefinitionDraftJson);
        if (!document.Succeeded)
        {
            return document.Failure!;
        }

        if (!document.Root!.TryGetPropertyValue("control_protocol", out var protocolNode))
        {
            return Failed(
                WorkflowLoopRegionDraftPatchStatus.LoopRegionNotFound,
                "LOOP_REGION_NOT_FOUND");
        }

        if (protocolNode is not JsonObject protocol)
        {
            return Failed(
                WorkflowLoopRegionDraftPatchStatus.ControlProtocolNotObject,
                "CONTROL_PROTOCOL_NOT_OBJECT");
        }

        if (!protocol.TryGetPropertyValue("loop_regions", out var regionsNode) ||
            regionsNode is not JsonArray loopRegions)
        {
            return Failed(
                WorkflowLoopRegionDraftPatchStatus.LoopRegionsNotArray,
                "LOOP_REGIONS_NOT_ARRAY");
        }

        for (var index = 0; index < loopRegions.Count; index++)
        {
            if (loopRegions[index] is not JsonObject region)
            {
                return Failed(
                    WorkflowLoopRegionDraftPatchStatus.LoopRegionNotObject,
                    "LOOP_REGION_NOT_OBJECT");
            }

            if (!string.Equals(
                    GetString(region, "loop_id"),
                    loopId,
                    StringComparison.Ordinal))
            {
                continue;
            }

            var clearFailure = ClearNodeLoopId(
                document.Nodes!,
                GetString(region, "start_node_id"),
                loopId);
            clearFailure ??= ClearNodeLoopId(
                document.Nodes!,
                GetString(region, "judge_node_id"),
                loopId);
            if (clearFailure is not null)
            {
                return clearFailure;
            }

            loopRegions.RemoveAt(index);
            NormalizeProtocol(protocol, loopRegions);
            return Succeeded(document.Root!);
        }

        return Failed(
            WorkflowLoopRegionDraftPatchStatus.LoopRegionNotFound,
            "LOOP_REGION_NOT_FOUND");
    }

    private static DocumentRead ReadDocument(string workflowDefinitionDraftJson)
    {
        JsonNode? parsed;
        try
        {
            parsed = JsonNode.Parse(workflowDefinitionDraftJson);
        }
        catch (JsonException)
        {
            return DocumentRead.Rejected(
                Failed(
                    WorkflowLoopRegionDraftPatchStatus.JsonInvalid,
                    "WORKFLOW_DRAFT_JSON_INVALID"));
        }

        if (parsed is not JsonObject root)
        {
            return DocumentRead.Rejected(
                Failed(
                    WorkflowLoopRegionDraftPatchStatus.RootNotObject,
                    "WORKFLOW_DRAFT_ROOT_NOT_OBJECT"));
        }

        if (root["nodes"] is not JsonArray nodes)
        {
            return DocumentRead.Rejected(
                Failed(
                    WorkflowLoopRegionDraftPatchStatus.NodesMissing,
                    "WORKFLOW_DRAFT_NODES_MISSING"));
        }

        var nodesById = new Dictionary<string, JsonObject>(StringComparer.Ordinal);
        foreach (var node in nodes)
        {
            if (node is not JsonObject nodeObject)
            {
                return DocumentRead.Rejected(
                    Failed(
                        WorkflowLoopRegionDraftPatchStatus.NodeInstanceIdRequired,
                        "NODE_INSTANCE_ID_REQUIRED"));
            }

            var nodeId = GetString(nodeObject, "node_instance_id");
            if (string.IsNullOrWhiteSpace(nodeId) || !nodesById.TryAdd(nodeId, nodeObject))
            {
                return DocumentRead.Rejected(
                    Failed(
                        WorkflowLoopRegionDraftPatchStatus.NodeInstanceIdRequired,
                        "NODE_INSTANCE_ID_REQUIRED"));
            }
        }

        return DocumentRead.Success(root, nodesById);
    }

    private static ProtocolRead GetOrCreateProtocol(JsonObject root)
    {
        if (!root.TryGetPropertyValue("control_protocol", out var protocolNode))
        {
            var created = new JsonObject();
            root["control_protocol"] = created;
            return ProtocolRead.Success(created);
        }

        return protocolNode is JsonObject protocol
            ? ProtocolRead.Success(protocol)
            : ProtocolRead.Rejected(
                Failed(
                    WorkflowLoopRegionDraftPatchStatus.ControlProtocolNotObject,
                    "CONTROL_PROTOCOL_NOT_OBJECT"));
    }

    private static LoopRegionsRead GetOrCreateLoopRegions(JsonObject protocol)
    {
        if (!protocol.TryGetPropertyValue("loop_regions", out var regionsNode))
        {
            var created = new JsonArray();
            protocol["loop_regions"] = created;
            return LoopRegionsRead.Success(created);
        }

        return regionsNode is JsonArray regions
            ? LoopRegionsRead.Success(regions)
            : LoopRegionsRead.Rejected(
                Failed(
                    WorkflowLoopRegionDraftPatchStatus.LoopRegionsNotArray,
                    "LOOP_REGIONS_NOT_ARRAY"));
    }

    private static void ApplyDraft(JsonObject region, WorkflowLoopRegionDraft draft)
    {
        region["loop_id"] = draft.LoopId;
        region["start_node_id"] = draft.StartNodeId;
        region["judge_node_id"] = draft.JudgeNodeId;
        var bodyNodes = new JsonArray();
        foreach (var nodeId in draft.BodyNodeIds)
        {
            bodyNodes.Add(nodeId);
        }

        region["body_node_ids"] = bodyNodes;
        if (draft.EndNodeId is null)
        {
            region.Remove("end_node_id");
        }
        else
        {
            region["end_node_id"] = draft.EndNodeId;
        }

        region["max_iterations"] = draft.MaxIterations;
        region["input_mode"] = WorkflowLoopRegionDraft.SupportedInputMode;
        region["continue_branch"] = WorkflowLoopRegionDraft.ContinueLoopBranch;
        region["end_branch"] = WorkflowLoopRegionDraft.EndLoopBranch;
        region["enabled"] = draft.Enabled;
    }

    private static IEnumerable<string> RegionNodeIds(WorkflowLoopRegionDraft draft)
    {
        return new[] { draft.StartNodeId, draft.JudgeNodeId }
            .Concat(draft.BodyNodeIds)
            .Concat(draft.EndNodeId is null ? [] : [draft.EndNodeId]);
    }

    private static IEnumerable<string> ReadRegionNodeIds(JsonObject region)
    {
        var result = new List<string>();
        AddIfPresent(result, GetString(region, "start_node_id"));
        AddIfPresent(result, GetString(region, "judge_node_id"));
        AddIfPresent(result, GetString(region, "end_node_id"));
        if (region["body_node_ids"] is JsonArray bodyNodes)
        {
            foreach (var bodyNode in bodyNodes)
            {
                if (bodyNode is JsonValue value &&
                    value.TryGetValue<string>(out var nodeId))
                {
                    AddIfPresent(result, nodeId);
                }
            }
        }

        return result;
    }

    private static void AddIfPresent(ICollection<string> values, string value)
    {
        if (!string.IsNullOrWhiteSpace(value))
        {
            values.Add(value);
        }
    }

    private static WorkflowLoopRegionDraftPatchResult? SynchronizeNodeLoopIds(
        IReadOnlyDictionary<string, JsonObject> nodes,
        string? oldLoopId,
        string? oldStartNodeId,
        string? oldJudgeNodeId,
        WorkflowLoopRegionDraft draft)
    {
        if (!string.IsNullOrWhiteSpace(oldLoopId))
        {
            var clearFailure = ClearNodeLoopId(nodes, oldStartNodeId, oldLoopId);
            clearFailure ??= ClearNodeLoopId(nodes, oldJudgeNodeId, oldLoopId);
            if (clearFailure is not null)
            {
                return clearFailure;
            }
        }

        var setFailure = SetNodeLoopId(nodes, draft.StartNodeId, draft.LoopId);
        setFailure ??= SetNodeLoopId(nodes, draft.JudgeNodeId, draft.LoopId);
        return setFailure;
    }

    private static WorkflowLoopRegionDraftPatchResult? ClearNodeLoopId(
        IReadOnlyDictionary<string, JsonObject> nodes,
        string? nodeId,
        string loopId)
    {
        if (string.IsNullOrWhiteSpace(nodeId) || !nodes.TryGetValue(nodeId, out var node))
        {
            return null;
        }

        if (!node.TryGetPropertyValue("config", out var configNode))
        {
            return null;
        }

        if (configNode is not JsonObject config)
        {
            return Failed(
                WorkflowLoopRegionDraftPatchStatus.NodeConfigNotObject,
                "NODE_CONFIG_NOT_OBJECT");
        }

        if (string.Equals(GetString(config, "loop_id"), loopId, StringComparison.Ordinal))
        {
            config.Remove("loop_id");
        }

        return null;
    }

    private static WorkflowLoopRegionDraftPatchResult? SetNodeLoopId(
        IReadOnlyDictionary<string, JsonObject> nodes,
        string nodeId,
        string loopId)
    {
        var node = nodes[nodeId];
        if (!node.TryGetPropertyValue("config", out var configNode))
        {
            var created = new JsonObject();
            node["config"] = created;
            created["loop_id"] = loopId;
            return null;
        }

        if (configNode is not JsonObject config)
        {
            return Failed(
                WorkflowLoopRegionDraftPatchStatus.NodeConfigNotObject,
                "NODE_CONFIG_NOT_OBJECT");
        }

        config["loop_id"] = loopId;
        return null;
    }

    private static void NormalizeProtocol(JsonObject protocol, JsonArray loopRegions)
    {
        protocol["version"] = "1.0";
        protocol["mode"] = loopRegions
            .OfType<JsonObject>()
            .Any(region => GetBool(region, "enabled"))
                ? "enabled"
                : "preview";
    }

    private static string GetString(JsonObject value, string propertyName)
    {
        return value[propertyName] is JsonValue property &&
            property.TryGetValue<string>(out var text)
                ? text
                : string.Empty;
    }

    private static bool GetBool(JsonObject value, string propertyName)
    {
        return value[propertyName] is JsonValue property &&
            property.TryGetValue<bool>(out var flag) &&
            flag;
    }

    private static WorkflowLoopRegionDraftPatchResult Succeeded(JsonObject root)
    {
        return new WorkflowLoopRegionDraftPatchResult
        {
            Status = WorkflowLoopRegionDraftPatchStatus.Succeeded,
            UpdatedWorkflowDefinitionDraftJson =
                root.ToJsonString(IndentedJsonOptions),
        };
    }

    private static WorkflowLoopRegionDraftPatchResult Failed(
        WorkflowLoopRegionDraftPatchStatus status,
        string warning)
    {
        return new WorkflowLoopRegionDraftPatchResult
        {
            Status = status,
            Warning = warning,
        };
    }

    private sealed record DocumentRead
    {
        public JsonObject? Root { get; init; }

        public IReadOnlyDictionary<string, JsonObject>? Nodes { get; init; }

        public WorkflowLoopRegionDraftPatchResult? Failure { get; init; }

        public bool Succeeded => Failure is null;

        public static DocumentRead Success(
            JsonObject root,
            IReadOnlyDictionary<string, JsonObject> nodes)
        {
            return new DocumentRead { Root = root, Nodes = nodes };
        }

        public static DocumentRead Rejected(WorkflowLoopRegionDraftPatchResult failure)
        {
            return new DocumentRead { Failure = failure };
        }
    }

    private sealed record ProtocolRead
    {
        public JsonObject? Protocol { get; init; }

        public WorkflowLoopRegionDraftPatchResult? Failure { get; init; }

        public bool Succeeded => Failure is null;

        public static ProtocolRead Success(JsonObject protocol)
        {
            return new ProtocolRead { Protocol = protocol };
        }

        public static ProtocolRead Rejected(WorkflowLoopRegionDraftPatchResult failure)
        {
            return new ProtocolRead { Failure = failure };
        }
    }

    private sealed record LoopRegionsRead
    {
        public JsonArray? Regions { get; init; }

        public WorkflowLoopRegionDraftPatchResult? Failure { get; init; }

        public bool Succeeded => Failure is null;

        public static LoopRegionsRead Success(JsonArray regions)
        {
            return new LoopRegionsRead { Regions = regions };
        }

        public static LoopRegionsRead Rejected(WorkflowLoopRegionDraftPatchResult failure)
        {
            return new LoopRegionsRead { Failure = failure };
        }
    }
}
