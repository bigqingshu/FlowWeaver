using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ResetNewDraftNodeInput()
    {
        lastSuggestedNewDraftNodeInstanceId = string.Empty;
        lastSuggestedNewDraftNodeConfigJson = "{}";
        SelectedNewDraftNodeDefinition = null;
        NewDraftNodeInstanceId = string.Empty;
        NewDraftNodeType = string.Empty;
        NewDraftNodeVersion = "1.0";
        NewDraftNodeDisplayName = string.Empty;
        NewDraftNodeConfigJson = "{}";
    }

    private void ApplySelectedNewDraftNodeDefinition(
        NodeDefinitionListItemViewModel definition)
    {
        NewDraftNodeType = definition.NodeType;
        NewDraftNodeVersion = string.IsNullOrWhiteSpace(definition.NodeVersion)
            ? "1.0"
            : definition.NodeVersion;

        if (string.IsNullOrWhiteSpace(NewDraftNodeDisplayName))
        {
            NewDraftNodeDisplayName = definition.DisplayNameText;
        }

        if (ShouldApplySuggestedNewDraftNodeInstanceId())
        {
            lastSuggestedNewDraftNodeInstanceId =
                BuildUniqueNewDraftNodeInstanceId(definition.NodeType);
            NewDraftNodeInstanceId = lastSuggestedNewDraftNodeInstanceId;
        }

        if (ShouldApplySuggestedNewDraftNodeConfigJson())
        {
            lastSuggestedNewDraftNodeConfigJson =
                NodeConfigDefaultBuilder.BuildJson(definition.ConfigSchemaDescriptor);
            NewDraftNodeConfigJson = lastSuggestedNewDraftNodeConfigJson;
        }
    }

    private (string? InputPort, string? OutputPort, string? SourceOutputPort) TryGetAutoWirePorts()
    {
        var definition = SelectedNewDraftNodeDefinition;
        if (definition is null)
        {
            return (null, null, null);
        }

        var inputPort = TryGetSingleInputPort(definition.InputPorts);
        if (inputPort is null)
        {
            return (null, null, null);
        }

        return (
            inputPort,
            TryGetPreferredOutputPort(definition.OutputPorts),
            TryGetSourceAutoWireOutputPort());
    }

    private string? TryGetSourceAutoWireOutputPort()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return null;
        }

        var sourceDefinition = FindNodeDefinition(SelectedWorkflowDefinitionNode);
        return sourceDefinition is null
            ? null
            : TryGetPreferredOutputPort(sourceDefinition.OutputPorts);
    }

    private static string? TryGetSingleInputPort(
        IReadOnlyList<NodePortDefinitionDto> inputPorts)
    {
        return inputPorts.Count == 1 ? inputPorts[0].Name : null;
    }

    private static string? TryGetPreferredOutputPort(
        IReadOnlyList<NodePortDefinitionDto> outputPorts)
    {
        if (outputPorts.Count == 0)
        {
            return null;
        }

        var outPort = outputPorts.FirstOrDefault(port =>
            string.Equals(port.Name, "out", StringComparison.Ordinal));
        if (outPort is not null)
        {
            return outPort.Name;
        }

        return outputPorts.Count == 1 ? outputPorts[0].Name : null;
    }

    private bool ShouldApplySuggestedNewDraftNodeInstanceId()
    {
        return string.IsNullOrWhiteSpace(NewDraftNodeInstanceId)
            || string.Equals(
                NewDraftNodeInstanceId,
                lastSuggestedNewDraftNodeInstanceId,
                StringComparison.Ordinal);
    }

    private bool ShouldApplySuggestedNewDraftNodeConfigJson()
    {
        return string.IsNullOrWhiteSpace(NewDraftNodeConfigJson)
            || string.Equals(NewDraftNodeConfigJson.Trim(), "{}", StringComparison.Ordinal)
            || string.Equals(
                NewDraftNodeConfigJson,
                lastSuggestedNewDraftNodeConfigJson,
                StringComparison.Ordinal);
    }

    private string BuildUniqueNewDraftNodeInstanceId(string nodeType)
    {
        var baseId = BuildNewDraftNodeInstanceIdBase(nodeType);
        var existingIds = WorkflowDefinitionDraftStructure?.Nodes
            .Select(node => node.NodeInstanceId)
            .ToHashSet(StringComparer.Ordinal)
            ?? new HashSet<string>(StringComparer.Ordinal);

        var candidate = baseId;
        var suffix = 2;
        while (existingIds.Contains(candidate))
        {
            candidate = $"{baseId}_{suffix}";
            suffix++;
        }

        return candidate;
    }

    private static string BuildNewDraftNodeInstanceIdBase(string nodeType)
    {
        var source = string.IsNullOrWhiteSpace(nodeType)
            ? "node"
            : nodeType.Trim();

        if (source.EndsWith("Node", StringComparison.Ordinal) && source.Length > 4)
        {
            source = source[..^4];
        }

        return BuildSnakeCaseIdentifier(source, "node");
    }

    partial void OnSelectedNewDraftNodeDefinitionChanged(
        NodeDefinitionListItemViewModel? value)
    {
        if (value is not null)
        {
            ApplySelectedNewDraftNodeDefinition(value);
        }
    }

    partial void OnNewDraftNodeInstanceIdChanged(string value)
    {
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftNodeTypeChanged(string value)
    {
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftNodeVersionChanged(string value)
    {
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftNodeConfigJsonChanged(string value)
    {
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }
}
