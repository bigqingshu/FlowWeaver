using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Avalonia_UI.Api;

namespace Avalonia_UI.Models;

public sealed record NodeTableInputBindingCandidate
{
    public string SourceNodeInstanceId { get; init; } = string.Empty;

    public string SourceNodeDisplayName { get; init; } = string.Empty;

    public string OutputSlot { get; init; } = string.Empty;

    public string OutputSlotDisplayName { get; init; } = string.Empty;

    public string OutputRole { get; init; } = string.Empty;

    public string? StorageKind { get; init; }

    public string? LogicalTableId { get; init; }

    public string? RecentTableRefId { get; init; }

    public int? RecentVersion { get; init; }

    public string? RecentLifecycleStatus { get; init; }
}

public sealed record NodeTableExistingOutputTargetCandidate
{
    public string WorkflowRunId { get; init; } = string.Empty;

    public string StorageKind { get; init; } = string.Empty;

    public string Role { get; init; } = string.Empty;

    public string LogicalTableId { get; init; } = string.Empty;

    public string TargetKind => StorageKind == "MEMORY"
        ? NodeTableOutputTargetDraft.ExistingMemoryTargetKind
        : NodeTableOutputTargetDraft.ExistingRuntimeSqlTargetKind;

    public string? LatestTableRefId { get; init; }

    public int Version { get; init; }

    public string LifecycleStatus { get; init; } = string.Empty;
}

public sealed record NodeTableBindingCandidateSet
{
    public IReadOnlyList<NodeTableInputBindingCandidate> InputCandidates { get; init; } = [];

    public IReadOnlyList<NodeTableExistingOutputTargetCandidate> ExistingOutputTargets { get; init; } = [];
}

public sealed class NodeTableBindingCandidateBuilder
{
    private CandidateCacheKey? cachedKey;
    private NodeTableBindingCandidateSet? cachedResult;

    public NodeTableBindingCandidateSet Build(
        WorkflowDefinitionDraftSnapshot snapshot,
        string draftRevision,
        string selectedNodeInstanceId,
        string catalogHash,
        IReadOnlyCollection<NodeDefinitionDto> nodeDefinitions,
        IReadOnlyCollection<TableRefDto> tableCatalog)
    {
        var key = new CandidateCacheKey(
            draftRevision,
            selectedNodeInstanceId,
            catalogHash);
        if (key == cachedKey && cachedResult is not null)
        {
            return cachedResult;
        }

        cachedKey = key;
        cachedResult = BuildCore(
            snapshot,
            selectedNodeInstanceId,
            nodeDefinitions,
            tableCatalog);
        return cachedResult;
    }

    public void Invalidate()
    {
        cachedKey = null;
        cachedResult = null;
    }

    private static NodeTableBindingCandidateSet BuildCore(
        WorkflowDefinitionDraftSnapshot snapshot,
        string selectedNodeInstanceId,
        IReadOnlyCollection<NodeDefinitionDto> nodeDefinitions,
        IReadOnlyCollection<TableRefDto> tableCatalog)
    {
        if (!snapshot.Succeeded || snapshot.Root.ValueKind != JsonValueKind.Object)
        {
            return new NodeTableBindingCandidateSet();
        }

        var nodes = ReadNodes(snapshot.Root);
        if (!nodes.TryGetValue(selectedNodeInstanceId, out var selectedNode))
        {
            return new NodeTableBindingCandidateSet();
        }

        var directUpstreamIds = ReadDirectUpstreamIds(
            snapshot.Root,
            selectedNode.Element,
            selectedNodeInstanceId);
        var definitions = nodeDefinitions.ToDictionary(
            definition => (definition.NodeType, definition.NodeVersion),
            definition => definition);
        var recentTables = tableCatalog
            .Where(table => directUpstreamIds.Contains(table.SourceNodeInstanceId ?? string.Empty))
            .ToArray();
        var candidates = new List<NodeTableInputBindingCandidate>();
        var declaredSourceSlots = new HashSet<(string SourceNodeId, string OutputSlot)>();

        foreach (var upstreamId in directUpstreamIds)
        {
            if (!nodes.TryGetValue(upstreamId, out var upstreamNode) ||
                !definitions.TryGetValue(
                    (upstreamNode.NodeType, upstreamNode.NodeVersion),
                    out var definition))
            {
                continue;
            }

            var configuredOutputs = NodeTableBindingsDraftReader
                .Read(snapshot, upstreamId)
                .OutputTargets
                .ToDictionary(target => target.Slot, target => target, StringComparer.Ordinal);
            foreach (var slot in definition.OutputTableSlots)
            {
                if (string.IsNullOrWhiteSpace(slot.Name))
                {
                    continue;
                }

                declaredSourceSlots.Add((upstreamId, slot.Name));
                configuredOutputs.TryGetValue(slot.Name, out var configuredTarget);
                var outputRole = configuredTarget?.IsCurrent == true
                    ? "CURRENT"
                    : configuredTarget is null
                        ? slot.DefaultRole
                        : "AUXILIARY";
                var recent = FindLatestRecentTable(
                    recentTables,
                    upstreamId,
                    slot.Name,
                    configuredTarget?.StorageKind,
                    configuredTarget?.LogicalTableId,
                    outputRole);
                candidates.Add(new NodeTableInputBindingCandidate
                {
                    SourceNodeInstanceId = upstreamId,
                    SourceNodeDisplayName = upstreamNode.DisplayName,
                    OutputSlot = slot.Name,
                    OutputSlotDisplayName = string.IsNullOrWhiteSpace(slot.DisplayName)
                        ? slot.Name
                        : slot.DisplayName,
                    OutputRole = outputRole,
                    StorageKind = configuredTarget?.StorageKind ?? recent?.StorageKind,
                    LogicalTableId = configuredTarget?.LogicalTableId ?? recent?.LogicalTableId,
                    RecentTableRefId = recent?.TableRefId,
                    RecentVersion = recent?.Version,
                    RecentLifecycleStatus = recent?.LifecycleStatus,
                });
            }
        }

        foreach (var table in recentTables
            .Where(table => !string.IsNullOrWhiteSpace(table.OutputSlot))
            .GroupBy(table => (
                SourceNodeId: table.SourceNodeInstanceId!,
                OutputSlot: table.OutputSlot!))
            .Select(group => group
                .OrderByDescending(table => table.Version)
                .ThenByDescending(table => table.CreatedAt)
                .First()))
        {
            var key = (table.SourceNodeInstanceId!, table.OutputSlot!);
            if (declaredSourceSlots.Contains(key))
            {
                continue;
            }

            nodes.TryGetValue(table.SourceNodeInstanceId!, out var sourceNode);
            candidates.Add(new NodeTableInputBindingCandidate
            {
                SourceNodeInstanceId = table.SourceNodeInstanceId!,
                SourceNodeDisplayName = sourceNode?.DisplayName ?? table.SourceNodeInstanceId!,
                OutputSlot = table.OutputSlot!,
                OutputSlotDisplayName = table.OutputSlot!,
                OutputRole = table.Role,
                StorageKind = table.StorageKind,
                LogicalTableId = table.LogicalTableId,
                RecentTableRefId = table.TableRefId,
                RecentVersion = table.Version,
                RecentLifecycleStatus = table.LifecycleStatus,
            });
        }

        return new NodeTableBindingCandidateSet
        {
            InputCandidates = candidates,
            ExistingOutputTargets = BuildExistingOutputTargets(tableCatalog),
        };
    }

    private static IReadOnlyList<NodeTableExistingOutputTargetCandidate>
        BuildExistingOutputTargets(IReadOnlyCollection<TableRefDto> tableCatalog)
    {
        return tableCatalog
            .Where(table =>
                table.StorageKind is "MEMORY" or "RUNTIME_SQL" &&
                !string.IsNullOrWhiteSpace(table.WorkflowRunId) &&
                !string.IsNullOrWhiteSpace(table.Role) &&
                !string.IsNullOrWhiteSpace(table.LogicalTableId))
            .GroupBy(table => (
                table.WorkflowRunId,
                table.StorageKind,
                table.Role,
                table.LogicalTableId))
            .Select(group => group
                .OrderByDescending(table => table.Version)
                .ThenByDescending(table => table.CreatedAt)
                .First())
            .Select(table => new NodeTableExistingOutputTargetCandidate
            {
                WorkflowRunId = table.WorkflowRunId,
                StorageKind = table.StorageKind,
                Role = table.Role,
                LogicalTableId = table.LogicalTableId,
                LatestTableRefId = table.TableRefId,
                Version = table.Version,
                LifecycleStatus = table.LifecycleStatus,
            })
            .OrderBy(candidate => candidate.StorageKind, StringComparer.Ordinal)
            .ThenBy(candidate => candidate.Role, StringComparer.Ordinal)
            .ThenBy(candidate => candidate.LogicalTableId, StringComparer.Ordinal)
            .ToArray();
    }

    private static TableRefDto? FindLatestRecentTable(
        IEnumerable<TableRefDto> tables,
        string sourceNodeId,
        string outputSlot,
        string? storageKind,
        string? logicalTableId,
        string outputRole)
    {
        return tables
            .Where(table =>
                string.Equals(table.SourceNodeInstanceId, sourceNodeId, StringComparison.Ordinal) &&
                string.Equals(table.OutputSlot, outputSlot, StringComparison.Ordinal) &&
                (storageKind is null || string.Equals(
                    table.StorageKind,
                    storageKind,
                    StringComparison.Ordinal)) &&
                (logicalTableId is null || string.Equals(
                    table.LogicalTableId,
                    logicalTableId,
                    StringComparison.Ordinal)) &&
                (string.IsNullOrWhiteSpace(outputRole) || string.Equals(
                    table.Role,
                    outputRole,
                    StringComparison.Ordinal)))
            .OrderByDescending(table => table.Version)
            .ThenByDescending(table => table.CreatedAt)
            .FirstOrDefault();
    }

    private static Dictionary<string, DraftNodeInfo> ReadNodes(JsonElement root)
    {
        var result = new Dictionary<string, DraftNodeInfo>(StringComparer.Ordinal);
        if (!root.TryGetProperty("nodes", out var nodes) ||
            nodes.ValueKind != JsonValueKind.Array)
        {
            return result;
        }

        foreach (var node in nodes.EnumerateArray())
        {
            var nodeId = ReadString(node, "node_instance_id");
            if (node.ValueKind != JsonValueKind.Object || string.IsNullOrWhiteSpace(nodeId))
            {
                continue;
            }

            result[nodeId] = new DraftNodeInfo(
                node,
                ReadString(node, "node_type"),
                ReadString(node, "node_version"),
                ReadString(node, "display_name") is { Length: > 0 } displayName
                    ? displayName
                    : nodeId);
        }

        return result;
    }

    private static IReadOnlyList<string> ReadDirectUpstreamIds(
        JsonElement root,
        JsonElement selectedNode,
        string selectedNodeId)
    {
        var result = new List<string>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        if (selectedNode.TryGetProperty("dag_node", out var dagNode) &&
            dagNode.ValueKind == JsonValueKind.Object &&
            dagNode.TryGetProperty("upstream_node_ids", out var upstreamIds) &&
            upstreamIds.ValueKind == JsonValueKind.Array)
        {
            foreach (var upstreamId in upstreamIds.EnumerateArray())
            {
                if (upstreamId.ValueKind == JsonValueKind.String &&
                    upstreamId.GetString() is { Length: > 0 } value &&
                    seen.Add(value))
                {
                    result.Add(value);
                }
            }
        }

        if (!root.TryGetProperty("connections", out var connections) ||
            connections.ValueKind != JsonValueKind.Array)
        {
            return result;
        }

        foreach (var connection in connections.EnumerateArray())
        {
            if (!string.Equals(
                    ReadString(connection, "target_node_id"),
                    selectedNodeId,
                    StringComparison.Ordinal))
            {
                continue;
            }

            var sourceNodeId = ReadString(connection, "source_node_id");
            if (!string.IsNullOrWhiteSpace(sourceNodeId) && seen.Add(sourceNodeId))
            {
                result.Add(sourceNodeId);
            }
        }

        return result;
    }

    private static string ReadString(JsonElement element, string propertyName)
    {
        return element.ValueKind == JsonValueKind.Object &&
            element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.String
                ? property.GetString()?.Trim() ?? string.Empty
                : string.Empty;
    }

    private sealed record DraftNodeInfo(
        JsonElement Element,
        string NodeType,
        string NodeVersion,
        string DisplayName);

    private sealed record CandidateCacheKey(
        string DraftRevision,
        string SelectedNodeInstanceId,
        string CatalogHash);
}
