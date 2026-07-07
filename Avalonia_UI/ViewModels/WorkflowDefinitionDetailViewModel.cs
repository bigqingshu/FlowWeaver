using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public sealed class WorkflowDefinitionDetailViewModel
{
    public WorkflowDefinitionDetailViewModel(
        WorkflowDefinitionDto workflow,
        IEnumerable<WorkflowRevisionDto> revisions,
        DisplayTextFormatter? displayTextFormatter = null,
        NodeEditorResolver? nodeEditorResolver = null)
    {
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        nodeEditorResolver ??= new NodeEditorResolver(BuiltinNodeEditors.CreateRegistry());
        WorkflowId = workflow.WorkflowId;
        Name = workflow.Name;
        RevisionId = workflow.RevisionId;
        Version = workflow.Version;
        DefinitionHash = workflow.DefinitionHash;
        Status = workflow.Status;
        UpdatedAt = workflow.UpdatedAt;
        RawDefinitionJson = FormatJson(workflow.Definition);
        Nodes = new ObservableCollection<WorkflowDefinitionNodeListItemViewModel>(
            ReadNodes(workflow.Definition, DisplayTextFormatter, nodeEditorResolver));
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

    public DisplayTextFormatter DisplayTextFormatter { get; }

    public ObservableCollection<WorkflowDefinitionNodeListItemViewModel> Nodes { get; }

    public ObservableCollection<WorkflowDefinitionConnectionListItemViewModel> Connections { get; }

    public ObservableCollection<WorkflowRevisionListItemViewModel> Revisions { get; }

    public string VersionText => $"v{Version}";

    public string UpdatedAtText => UpdatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");

    public string NodeCountText => DisplayTextFormatter.FormatNodeCount(Nodes.Count);

    public string ConnectionCountText =>
        DisplayTextFormatter.FormatConnectionCount(Connections.Count);

    private static IEnumerable<WorkflowDefinitionNodeListItemViewModel> ReadNodes(
        JsonElement definition,
        DisplayTextFormatter displayTextFormatter,
        NodeEditorResolver nodeEditorResolver)
    {
        if (!TryGetArray(definition, "nodes", out var nodes))
        {
            yield break;
        }

        var displayOrder = 1;
        foreach (var node in nodes.EnumerateArray())
        {
            var nodeType = GetString(node, "node_type");
            var displayName = GetString(node, "display_name");
            yield return new WorkflowDefinitionNodeListItemViewModel(
                GetString(node, "node_instance_id"),
                nodeType,
                GetString(node, "node_version"),
                displayName,
                GetBool(node, "enabled", defaultValue: true),
                TryGetProperty(node, "config", out var config)
                    ? FormatJson(config)
                    : "{}",
                displayTextFormatter,
                nodeEditorResolver.Resolve(nodeType, displayName),
                displayOrder);
            displayOrder++;
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

public sealed class WorkflowDefinitionNodeListItemViewModel : ObservableObject
{
    private bool isBatchSelected;

    public WorkflowDefinitionNodeListItemViewModel(
        string nodeInstanceId,
        string nodeType,
        string nodeVersion,
        string displayName,
        bool enabled,
        string configJson,
        DisplayTextFormatter? displayTextFormatter = null,
        NodeEditorResolution? nodeEditorResolution = null,
        int displayOrder = 0)
    {
        NodeInstanceId = nodeInstanceId;
        NodeType = nodeType;
        NodeVersion = nodeVersion;
        DisplayName = displayName;
        Enabled = enabled;
        ConfigJson = configJson;
        DisplayOrder = displayOrder;
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        NodeEditorResolution = nodeEditorResolution
            ?? NodeEditorResolution.JsonFallback(
                nodeType,
                string.IsNullOrWhiteSpace(displayName) ? nodeType : displayName,
                hasRegisteredEditor: false);
    }

    public string NodeInstanceId { get; }

    public string NodeType { get; }

    public string NodeVersion { get; }

    public string DisplayName { get; }

    public bool Enabled { get; }

    public string ConfigJson { get; }

    public int DisplayOrder { get; }

    public DisplayTextFormatter DisplayTextFormatter { get; }

    public NodeEditorResolution NodeEditorResolution { get; }

    public bool IsBatchSelected
    {
        get => isBatchSelected;
        set => SetProperty(ref isBatchSelected, value);
    }

    public string TypeText => $"{NodeType}@{NodeVersion}";

    public string OrderText => DisplayOrder > 0 ? $"#{DisplayOrder}" : string.Empty;

    public string TitleText =>
        string.IsNullOrWhiteSpace(DisplayName) ? NodeInstanceId : DisplayName;

    public string NodeTypeDisplayText =>
        DisplayTextFormatter.FormatNodeDefinitionDisplayName(
            NodeType,
            string.IsNullOrWhiteSpace(NodeEditorResolution.DisplayName)
                ? NodeType
                : NodeEditorResolution.DisplayName);

    public string NodeSummaryText =>
        string.IsNullOrWhiteSpace(NodeTypeDisplayText)
            ? NodeInstanceId
            : $"{NodeInstanceId} / {NodeTypeDisplayText}";

    public string DisplayNameText =>
        string.IsNullOrWhiteSpace(DisplayName) ? "-" : DisplayName;

    public string EnabledText => DisplayTextFormatter.FormatEnabled(Enabled);

    public string NodeEditorStatusText =>
        DisplayTextFormatter.FormatNodeEditorStatus(NodeEditorResolution.StatusKey);

    public bool HasRegisteredNodeEditor => NodeEditorResolution.HasRegisteredEditor;

    public bool UsesJsonFallback => NodeEditorResolution.UsesJsonFallback;
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
        RawDefinitionJson = FormatJson(revision.Definition);
        CreatedAt = revision.CreatedAt;
        CreatedBy = revision.CreatedBy;
    }

    public string RevisionId { get; }

    public string WorkflowId { get; }

    public int Version { get; }

    public string DefinitionHash { get; }

    public string RawDefinitionJson { get; }

    public DateTimeOffset CreatedAt { get; }

    public string? CreatedBy { get; }

    public string VersionText => $"v{Version}";

    public string CreatedAtText => CreatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");

    public string CreatedByText =>
        string.IsNullOrWhiteSpace(CreatedBy) ? "-" : CreatedBy;

    private static string FormatJson(JsonElement element)
    {
        return JsonSerializer.Serialize(
            element,
            new JsonSerializerOptions { WriteIndented = true });
    }
}
