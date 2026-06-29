using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class WorkflowDefinitionDetailViewModel
{
    public WorkflowDefinitionDetailViewModel(
        WorkflowDefinitionDto workflow,
        IEnumerable<WorkflowRevisionDto> revisions)
    {
        WorkflowId = workflow.WorkflowId;
        Name = workflow.Name;
        RevisionId = workflow.RevisionId;
        Version = workflow.Version;
        DefinitionHash = workflow.DefinitionHash;
        Status = workflow.Status;
        UpdatedAt = workflow.UpdatedAt;
        RawDefinitionJson = FormatJson(workflow.Definition);
        Nodes = new ObservableCollection<WorkflowDefinitionNodeListItemViewModel>(
            ReadNodes(workflow.Definition));
        Connections = new ObservableCollection<WorkflowDefinitionConnectionListItemViewModel>(
            ReadConnections(workflow.Definition));
        Revisions = new ObservableCollection<WorkflowRevisionListItemViewModel>(
            revisions.Select(revision => new WorkflowRevisionListItemViewModel(revision)));
    }

    public string WorkflowId { get; }

    public string Name { get; }

    public string RevisionId { get; }

    public int Version { get; }

    public string DefinitionHash { get; }

    public string Status { get; }

    public DateTimeOffset UpdatedAt { get; }

    public string RawDefinitionJson { get; }

    public ObservableCollection<WorkflowDefinitionNodeListItemViewModel> Nodes { get; }

    public ObservableCollection<WorkflowDefinitionConnectionListItemViewModel> Connections { get; }

    public ObservableCollection<WorkflowRevisionListItemViewModel> Revisions { get; }

    public string VersionText => $"v{Version}";

    public string UpdatedAtText => UpdatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");

    public string NodeCountText => $"{Nodes.Count} node(s)";

    public string ConnectionCountText => $"{Connections.Count} connection(s)";

    private static IEnumerable<WorkflowDefinitionNodeListItemViewModel> ReadNodes(
        JsonElement definition)
    {
        if (!TryGetArray(definition, "nodes", out var nodes))
        {
            yield break;
        }

        foreach (var node in nodes.EnumerateArray())
        {
            yield return new WorkflowDefinitionNodeListItemViewModel(
                GetString(node, "node_instance_id"),
                GetString(node, "node_type"),
                GetString(node, "node_version"),
                GetString(node, "display_name"),
                GetBool(node, "enabled", defaultValue: true),
                TryGetProperty(node, "config", out var config)
                    ? FormatJson(config)
                    : "{}");
        }
    }

    private static IEnumerable<WorkflowDefinitionConnectionListItemViewModel> ReadConnections(
        JsonElement definition)
    {
        if (!TryGetArray(definition, "connections", out var connections))
        {
            yield break;
        }

        foreach (var connection in connections.EnumerateArray())
        {
            yield return new WorkflowDefinitionConnectionListItemViewModel(
                GetString(connection, "connection_id"),
                GetString(connection, "source_node_id"),
                GetString(connection, "source_port"),
                GetString(connection, "target_node_id"),
                GetString(connection, "target_port"));
        }
    }

    private static bool TryGetArray(
        JsonElement element,
        string propertyName,
        out JsonElement array)
    {
        if (TryGetProperty(element, propertyName, out array)
            && array.ValueKind == JsonValueKind.Array)
        {
            return true;
        }

        array = default;
        return false;
    }

    private static bool TryGetProperty(
        JsonElement element,
        string propertyName,
        out JsonElement value)
    {
        if (element.ValueKind == JsonValueKind.Object
            && element.TryGetProperty(propertyName, out value))
        {
            return true;
        }

        value = default;
        return false;
    }

    private static string GetString(JsonElement element, string propertyName)
    {
        if (TryGetProperty(element, propertyName, out var value)
            && value.ValueKind == JsonValueKind.String)
        {
            return value.GetString() ?? string.Empty;
        }

        return string.Empty;
    }

    private static bool GetBool(
        JsonElement element,
        string propertyName,
        bool defaultValue)
    {
        if (TryGetProperty(element, propertyName, out var value)
            && value.ValueKind is JsonValueKind.True or JsonValueKind.False)
        {
            return value.GetBoolean();
        }

        return defaultValue;
    }

    private static string FormatJson(JsonElement element)
    {
        return JsonSerializer.Serialize(
            element,
            new JsonSerializerOptions { WriteIndented = true });
    }
}

public sealed class WorkflowDefinitionNodeListItemViewModel
{
    public WorkflowDefinitionNodeListItemViewModel(
        string nodeInstanceId,
        string nodeType,
        string nodeVersion,
        string displayName,
        bool enabled,
        string configJson)
    {
        NodeInstanceId = nodeInstanceId;
        NodeType = nodeType;
        NodeVersion = nodeVersion;
        DisplayName = displayName;
        Enabled = enabled;
        ConfigJson = configJson;
    }

    public string NodeInstanceId { get; }

    public string NodeType { get; }

    public string NodeVersion { get; }

    public string DisplayName { get; }

    public bool Enabled { get; }

    public string ConfigJson { get; }

    public string TypeText => $"{NodeType}@{NodeVersion}";

    public string DisplayNameText =>
        string.IsNullOrWhiteSpace(DisplayName) ? "-" : DisplayName;

    public string EnabledText => Enabled ? "enabled" : "disabled";
}

public sealed class WorkflowDefinitionConnectionListItemViewModel
{
    public WorkflowDefinitionConnectionListItemViewModel(
        string connectionId,
        string sourceNodeId,
        string sourcePort,
        string targetNodeId,
        string targetPort)
    {
        ConnectionId = connectionId;
        SourceNodeId = sourceNodeId;
        SourcePort = sourcePort;
        TargetNodeId = targetNodeId;
        TargetPort = targetPort;
    }

    public string ConnectionId { get; }

    public string SourceNodeId { get; }

    public string SourcePort { get; }

    public string TargetNodeId { get; }

    public string TargetPort { get; }

    public string EdgeText => $"{SourceNodeId}.{SourcePort} -> {TargetNodeId}.{TargetPort}";
}

public sealed class WorkflowRevisionListItemViewModel
{
    public WorkflowRevisionListItemViewModel(WorkflowRevisionDto revision)
    {
        RevisionId = revision.RevisionId;
        WorkflowId = revision.WorkflowId;
        Version = revision.Version;
        DefinitionHash = revision.DefinitionHash;
        CreatedAt = revision.CreatedAt;
        CreatedBy = revision.CreatedBy;
    }

    public string RevisionId { get; }

    public string WorkflowId { get; }

    public int Version { get; }

    public string DefinitionHash { get; }

    public DateTimeOffset CreatedAt { get; }

    public string? CreatedBy { get; }

    public string VersionText => $"v{Version}";

    public string CreatedAtText => CreatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");

    public string CreatedByText =>
        string.IsNullOrWhiteSpace(CreatedBy) ? "-" : CreatedBy;
}
