using System;
using System.Linq;
using System.Text.Json;
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

    private void NotifyWorkflowDefinitionNodeActionCommandsChanged()
    {
        CopyWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        DeleteSelectedWorkflowDefinitionDraftNodesCommand.NotifyCanExecuteChanged();
        MoveSelectedWorkflowDefinitionDraftNodeUpCommand.NotifyCanExecuteChanged();
        MoveSelectedWorkflowDefinitionDraftNodeDownCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionDisabledReasonsChanged();
    }

    partial void OnSelectedWorkflowDefinitionDraftNodeInstanceIdChanged(string value)
    {
        DeleteWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }
}
