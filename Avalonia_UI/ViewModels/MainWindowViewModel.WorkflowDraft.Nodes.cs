using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanAddWorkflowDefinitionDraftNode()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.IsNullOrWhiteSpace(NewDraftNodeInstanceId)
            && !string.IsNullOrWhiteSpace(NewDraftNodeType)
            && !string.IsNullOrWhiteSpace(NewDraftNodeVersion)
            && !string.IsNullOrWhiteSpace(NewDraftNodeConfigJson);
    }

    private bool CanDeleteWorkflowDefinitionDraftNode()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && FindDraftNode(SelectedWorkflowDefinitionNode.NodeInstanceId) is not null;
    }

    private bool CanDeleteSelectedWorkflowDefinitionDraftNodes()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && WorkflowDefinitionDraftNodes.Any(node =>
                node.IsBatchSelected
                && FindDraftNode(node.NodeInstanceId) is not null);
    }

    private bool CanCopyWorkflowDefinitionDraftNode()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && FindDraftNode(SelectedWorkflowDefinitionNode.NodeInstanceId) is not null;
    }

    private bool CanMoveSelectedWorkflowDefinitionDraftNodeUp()
    {
        return CanMoveSelectedWorkflowDefinitionDraftNode(offset: -1);
    }

    private bool CanMoveSelectedWorkflowDefinitionDraftNodeDown()
    {
        return CanMoveSelectedWorkflowDefinitionDraftNode(offset: 1);
    }

    private bool CanMoveSelectedWorkflowDefinitionDraftNode(int offset)
    {
        if (!CanUseEngineActions ||
            WorkflowDefinitionDetail is null ||
            SelectedWorkflowDefinitionNode is null ||
            !HasWorkflowDefinitionDraft ||
            IsWorkflowDefinitionDraftBusy ||
            HasWorkflowDefinitionRevisionConflict)
        {
            return false;
        }

        var index = WorkflowDefinitionDraftNodes.IndexOf(SelectedWorkflowDefinitionNode);
        var targetIndex = index + offset;
        return index >= 0 &&
            targetIndex >= 0 &&
            targetIndex < WorkflowDefinitionDraftNodes.Count;
    }

    private string? GetWorkflowDefinitionNodeMutationDisabledReason()
    {
        if (IsWorkflowDefinitionDraftBusy)
        {
            return T("action.disabled.busy");
        }

        if (!CanUseEngineActions)
        {
            return T("action.disabled.engine_not_connected");
        }

        if (WorkflowDefinitionDetail is null || !HasWorkflowDefinitionDraft)
        {
            return T("action.disabled.no_workflow_definition");
        }

        if (HasWorkflowDefinitionRevisionConflict)
        {
            return T("action.disabled.revision_conflict");
        }

        return null;
    }

    private string? GetSelectedWorkflowDefinitionNodeMutationDisabledReason()
    {
        var commonReason = GetWorkflowDefinitionNodeMutationDisabledReason();
        if (commonReason is not null)
        {
            return commonReason;
        }

        if (SelectedWorkflowDefinitionNode is null)
        {
            return T("action.disabled.no_workflow_node_selected");
        }

        if (FindDraftNode(SelectedWorkflowDefinitionNode.NodeInstanceId) is null)
        {
            return T("action.disabled.workflow_node_missing");
        }

        return null;
    }

    private string? GetSelectedWorkflowDefinitionDraftNodesMutationDisabledReason()
    {
        var commonReason = GetWorkflowDefinitionNodeMutationDisabledReason();
        if (commonReason is not null)
        {
            return commonReason;
        }

        var selectedNodes = WorkflowDefinitionDraftNodes
            .Where(node => node.IsBatchSelected)
            .ToArray();
        if (selectedNodes.Length == 0)
        {
            return T("action.disabled.no_workflow_nodes_checked");
        }

        return selectedNodes.Any(node => FindDraftNode(node.NodeInstanceId) is null)
            ? T("action.disabled.workflow_node_missing")
            : null;
    }

    private string? GetMoveSelectedWorkflowDefinitionDraftNodeDisabledReason(int offset)
    {
        var selectedReason = GetSelectedWorkflowDefinitionNodeMutationDisabledReason();
        if (selectedReason is not null)
        {
            return selectedReason;
        }

        var index = WorkflowDefinitionDraftNodes.IndexOf(SelectedWorkflowDefinitionNode!);
        var targetIndex = index + offset;
        if (index < 0)
        {
            return T("action.disabled.workflow_node_missing");
        }

        if (targetIndex < 0)
        {
            return T("action.disabled.workflow_node_at_top");
        }

        return targetIndex >= WorkflowDefinitionDraftNodes.Count
            ? T("action.disabled.workflow_node_at_bottom")
            : null;
    }

    public string? CopyWorkflowDefinitionDraftNodeDisabledReasonText =>
        GetSelectedWorkflowDefinitionNodeMutationDisabledReason();

    public string? DeleteWorkflowDefinitionDraftNodeDisabledReasonText =>
        GetSelectedWorkflowDefinitionNodeMutationDisabledReason();

    public string? DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText =>
        GetSelectedWorkflowDefinitionDraftNodesMutationDisabledReason();

    public string? MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText =>
        GetMoveSelectedWorkflowDefinitionDraftNodeDisabledReason(offset: -1);

    public string? MoveSelectedWorkflowDefinitionDraftNodeDownDisabledReasonText =>
        GetMoveSelectedWorkflowDefinitionDraftNodeDisabledReason(offset: 1);

    [RelayCommand(CanExecute = nameof(CanAddWorkflowDefinitionDraftNode))]
    private void AddWorkflowDefinitionDraftNode()
    {
        var autoWirePorts = TryGetAutoWirePorts();
        JsonElement config;
        try
        {
            using var parsed = JsonDocument.Parse(NewDraftNodeConfigJson);
            config = parsed.RootElement.Clone();
        }
        catch (JsonException)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_add_failed");
            WorkflowDefinitionValidationErrorMessage =
                T("definition.node_add_config_json_invalid");
            ShowWorkflowDefinitionNotification(
                "workflow.definition.add_node",
                UiNotificationKind.Error);
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.AddNode(
            WorkflowDefinitionDraftJson,
            NewDraftNodeInstanceId,
            NewDraftNodeType,
            NewDraftNodeVersion,
            NewDraftNodeDisplayName,
            config,
            SelectedWorkflowDefinitionNode?.NodeInstanceId,
            autoWirePorts.InputPort,
            autoWirePorts.OutputPort,
            autoWirePorts.SourceOutputPort);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_add_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.add_node",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(NewDraftNodeInstanceId);
        WorkflowDefinitionValidationMessage =
            patchResult.AddedConnections.Count > 0
                ? T("definition.node_added_with_connections")
                : T("definition.node_added");
        WorkflowDefinitionValidationErrorMessage =
            FormatAutoWiredConnectionsMessage(
                patchResult.RemovedConnections,
                patchResult.AddedConnections);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.add_node",
            UiNotificationKind.Success);
        ResetNewDraftNodeInput();
    }

    [RelayCommand(CanExecute = nameof(CanDeleteWorkflowDefinitionDraftNode))]
    private void DeleteWorkflowDefinitionDraftNode()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.DeleteNodeWithLinearBridge(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_delete_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.delete_node",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage =
            patchResult.AddedConnections.Count > 0
                ? T("definition.node_deleted_with_rewired_connections")
                : patchResult.RemovedConnections.Count > 0
                ? T("definition.node_deleted_with_connections")
                : T("definition.node_deleted");
        WorkflowDefinitionValidationErrorMessage =
            patchResult.AddedConnections.Count > 0
                ? FormatDeletedRewiredConnectionsMessage(
                    patchResult.RemovedConnections,
                    patchResult.AddedConnections)
                : FormatRemovedConnectionsMessage(patchResult.RemovedConnections);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.delete_node",
            UiNotificationKind.Success);
    }

    [RelayCommand(CanExecute = nameof(CanDeleteSelectedWorkflowDefinitionDraftNodes))]
    private void DeleteSelectedWorkflowDefinitionDraftNodes()
    {
        var selectedNodeIds = WorkflowDefinitionDraftNodes
            .Where(node => node.IsBatchSelected)
            .Select(node => node.NodeInstanceId)
            .ToArray();
        if (selectedNodeIds.Length == 0)
        {
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.DeleteNodes(
            WorkflowDefinitionDraftJson,
            selectedNodeIds);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_delete_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.delete_nodes",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage =
            patchResult.RemovedConnections.Count > 0
                ? F(
                    "format.workflow_definition_nodes_deleted_with_connections",
                    selectedNodeIds.Length)
                : F("format.workflow_definition_nodes_deleted", selectedNodeIds.Length);
        WorkflowDefinitionValidationErrorMessage =
            FormatRemovedConnectionsMessage(patchResult.RemovedConnections);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.delete_nodes",
            UiNotificationKind.Success);
    }

    [RelayCommand(CanExecute = nameof(CanCopyWorkflowDefinitionDraftNode))]
    private void CopyWorkflowDefinitionDraftNode()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.CopyNode(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_copy_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.copy_node",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        if (!string.IsNullOrWhiteSpace(patchResult.AddedNodeInstanceId))
        {
            SelectWorkflowDefinitionDraftNode(patchResult.AddedNodeInstanceId);
        }

        WorkflowDefinitionValidationMessage = T("definition.node_copied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.copy_node",
            UiNotificationKind.Success);
    }

    [RelayCommand(CanExecute = nameof(CanMoveSelectedWorkflowDefinitionDraftNodeUp))]
    private void MoveSelectedWorkflowDefinitionDraftNodeUp()
    {
        MoveSelectedWorkflowDefinitionDraftNode(offset: -1);
    }

    [RelayCommand(CanExecute = nameof(CanMoveSelectedWorkflowDefinitionDraftNodeDown))]
    private void MoveSelectedWorkflowDefinitionDraftNodeDown()
    {
        MoveSelectedWorkflowDefinitionDraftNode(offset: 1);
    }

    private void MoveSelectedWorkflowDefinitionDraftNode(int offset)
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var nodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        var patchResult = WorkflowDefinitionDraftNodePatcher.MoveNodeWithLinearRewire(
            WorkflowDefinitionDraftJson,
            nodeInstanceId,
            offset);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_move_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.move_node",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(nodeInstanceId);
        WorkflowDefinitionValidationMessage =
            patchResult.AddedConnections.Count > 0
                ? T("definition.node_moved_with_rewired_connections")
                : T("definition.node_moved");
        WorkflowDefinitionValidationErrorMessage =
            patchResult.AddedConnections.Count > 0
                ? FormatMovedRewiredConnectionsMessage(
                    patchResult.RemovedConnections,
                    patchResult.AddedConnections)
                : null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.move_node",
            UiNotificationKind.Success);
    }

    private void RefreshWorkflowDefinitionDraftNodes()
    {
        var selectedNodeId = SelectedWorkflowDefinitionNode?.NodeInstanceId;
        var hadSelectedNode = !string.IsNullOrWhiteSpace(selectedNodeId);
        var batchSelectedNodeIds = WorkflowDefinitionDraftNodes
            .Where(node => node.IsBatchSelected)
            .Select(node => node.NodeInstanceId)
            .ToHashSet(StringComparer.Ordinal);

        foreach (var node in WorkflowDefinitionDraftNodes)
        {
            node.PropertyChanged -= OnWorkflowDefinitionDraftNodeItemPropertyChanged;
        }

        WorkflowDefinitionDraftNodes.Clear();

        if (WorkflowDefinitionDraftStructure is not null)
        {
            var displayOrder = 1;
            foreach (var node in WorkflowDefinitionDraftStructure.Nodes)
            {
                var nodeItem = new WorkflowDefinitionNodeListItemViewModel(
                    node.NodeInstanceId,
                    node.NodeType,
                    node.NodeVersion,
                    node.DisplayName,
                    node.Enabled,
                    node.ConfigJson,
                    DisplayTextFormatter,
                    _nodeEditorResolver.Resolve(node.NodeType, node.DisplayName),
                    displayOrder)
                {
                    IsBatchSelected = batchSelectedNodeIds.Contains(node.NodeInstanceId),
                };
                nodeItem.PropertyChanged += OnWorkflowDefinitionDraftNodeItemPropertyChanged;
                WorkflowDefinitionDraftNodes.Add(nodeItem);
                displayOrder++;
            }
        }

        SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault(node =>
            string.Equals(node.NodeInstanceId, selectedNodeId, StringComparison.Ordinal));
        if (SelectedWorkflowDefinitionNode is null && !hadSelectedNode)
        {
            SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault();
        }

        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        OnPropertyChanged(nameof(WorkflowLinearChainStatusText));
        RefreshWorkflowDefinitionBatchSelectionState();
    }

    private void SelectWorkflowDefinitionDraftNode(string nodeInstanceId)
    {
        SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault(node =>
            string.Equals(
                node.NodeInstanceId,
                nodeInstanceId,
                StringComparison.Ordinal));
    }

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

    private void ClearWorkflowDefinitionDraftBatchSelection()
    {
        foreach (var node in WorkflowDefinitionDraftNodes)
        {
            node.IsBatchSelected = false;
        }

        RefreshWorkflowDefinitionBatchSelectionState();
    }

    private void OnWorkflowDefinitionDraftNodeItemPropertyChanged(
        object? sender,
        PropertyChangedEventArgs args)
    {
        if (args.PropertyName == nameof(WorkflowDefinitionNodeListItemViewModel.IsBatchSelected))
        {
            RefreshWorkflowDefinitionBatchSelectionState();
        }
    }

    private void RefreshWorkflowDefinitionBatchSelectionState()
    {
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCountText));
        DeleteSelectedWorkflowDefinitionDraftNodesCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText));
    }

    private void ClearSelectedWorkflowDefinitionDraftNodeIfMissing()
    {
        if (string.IsNullOrWhiteSpace(SelectedWorkflowDefinitionDraftNodeInstanceId))
        {
            return;
        }

        if (WorkflowDefinitionDraftStructure?.Nodes.Any(node =>
            string.Equals(
                node.NodeInstanceId,
                SelectedWorkflowDefinitionDraftNodeInstanceId,
                StringComparison.Ordinal)) == true)
        {
            return;
        }

        SelectedWorkflowDefinitionDraftNodeInstanceId = string.Empty;
    }

    private WorkflowDefinitionDraftNode? FindDraftNode(string nodeInstanceId)
    {
        return WorkflowDefinitionDraftStructure?.Nodes.FirstOrDefault(node =>
            string.Equals(
                node.NodeInstanceId,
                nodeInstanceId,
                StringComparison.Ordinal));
    }

    private string? FormatRemovedConnectionsMessage(
        IReadOnlyList<WorkflowDefinitionDraftConnection> removedConnections)
    {
        if (removedConnections.Count == 0)
        {
            return null;
        }

        return F(
            "definition.node_delete_removed_connections",
            string.Join(
                Environment.NewLine,
                removedConnections.Select(FormatRelatedConnectionSummary)));
    }

    private string? FormatAutoWiredConnectionsMessage(
        IReadOnlyList<WorkflowDefinitionDraftConnection> removedConnections,
        IReadOnlyList<WorkflowDefinitionDraftConnection> addedConnections)
    {
        if (removedConnections.Count == 0 && addedConnections.Count == 0)
        {
            return null;
        }

        var removedText = removedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                removedConnections.Select(FormatRelatedConnectionSummary));
        var addedText = addedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                addedConnections.Select(FormatRelatedConnectionSummary));

        return F(
            "definition.node_add_rewired_connections",
            removedText,
            addedText);
    }

    private string? FormatDeletedRewiredConnectionsMessage(
        IReadOnlyList<WorkflowDefinitionDraftConnection> removedConnections,
        IReadOnlyList<WorkflowDefinitionDraftConnection> addedConnections)
    {
        if (removedConnections.Count == 0 && addedConnections.Count == 0)
        {
            return null;
        }

        var removedText = removedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                removedConnections.Select(FormatRelatedConnectionSummary));
        var addedText = addedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                addedConnections.Select(FormatRelatedConnectionSummary));

        return F(
            "definition.node_delete_rewired_connections",
            removedText,
            addedText);
    }

    private string? FormatMovedRewiredConnectionsMessage(
        IReadOnlyList<WorkflowDefinitionDraftConnection> removedConnections,
        IReadOnlyList<WorkflowDefinitionDraftConnection> addedConnections)
    {
        if (removedConnections.Count == 0 && addedConnections.Count == 0)
        {
            return null;
        }

        var removedText = removedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                removedConnections.Select(FormatRelatedConnectionSummary));
        var addedText = addedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                addedConnections.Select(FormatRelatedConnectionSummary));

        return F(
            "definition.node_move_rewired_connections",
            removedText,
            addedText);
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

    private void NotifyWorkflowDefinitionNodeActionCommandsChanged()
    {
        CopyWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        DeleteSelectedWorkflowDefinitionDraftNodesCommand.NotifyCanExecuteChanged();
        MoveSelectedWorkflowDefinitionDraftNodeUpCommand.NotifyCanExecuteChanged();
        MoveSelectedWorkflowDefinitionDraftNodeDownCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionDisabledReasonsChanged();
    }

    private void NotifyWorkflowDefinitionNodeActionDisabledReasonsChanged()
    {
        OnPropertyChanged(nameof(CopyWorkflowDefinitionDraftNodeDisabledReasonText));
        OnPropertyChanged(nameof(DeleteWorkflowDefinitionDraftNodeDisabledReasonText));
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText));
        OnPropertyChanged(nameof(MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText));
        OnPropertyChanged(nameof(MoveSelectedWorkflowDefinitionDraftNodeDownDisabledReasonText));
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

    partial void OnSelectedWorkflowDefinitionDraftNodeInstanceIdChanged(string value)
    {
        DeleteWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }
}
