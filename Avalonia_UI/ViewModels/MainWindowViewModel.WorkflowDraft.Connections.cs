using System;
using System.Linq;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public string ConnectionsSectionText => T("definition.connections");

    public string ShowConnectionsText => IsWorkflowConnectionsAdvancedVisible
        ? T("definition.hide_connections")
        : T("definition.show_connections");

    public string AddConnectionText => T("definition.add_connection");

    public string DeleteConnectionText => T("definition.delete_connection");

    public string ConnectionIdText => T("definition.connection_id");

    public string SourceNodeText => T("definition.source_node");

    public string SourcePortText => T("definition.source_port");

    public string TargetNodeText => T("definition.target_node");

    public string TargetPortText => T("definition.target_port");

    private bool CanAddWorkflowDefinitionDraftConnection()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.IsNullOrWhiteSpace(NewDraftConnectionId)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionSourceNodeId)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionSourcePort)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionTargetNodeId)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionTargetPort);
    }

    private bool CanDeleteWorkflowDefinitionDraftConnection()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.IsNullOrWhiteSpace(SelectedWorkflowDefinitionDraftConnectionId);
    }

    [RelayCommand(CanExecute = nameof(CanAddWorkflowDefinitionDraftConnection))]
    private void AddWorkflowDefinitionDraftConnection()
    {
        var patchResult = WorkflowDefinitionDraftConnectionPatcher.AddConnection(
            WorkflowDefinitionDraftJson,
            NewDraftConnectionId,
            NewDraftConnectionSourceNodeId,
            NewDraftConnectionSourcePort,
            NewDraftConnectionTargetNodeId,
            NewDraftConnectionTargetPort);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.connection_add_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage = T("definition.connection_added");
        WorkflowDefinitionValidationErrorMessage = null;
        ResetNewDraftConnectionInput();
    }

    [RelayCommand(CanExecute = nameof(CanDeleteWorkflowDefinitionDraftConnection))]
    private void DeleteWorkflowDefinitionDraftConnection()
    {
        var patchResult = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionDraftConnectionId);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.connection_delete_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage = T("definition.connection_deleted");
        WorkflowDefinitionValidationErrorMessage = null;
    }

    private void ClearSelectedWorkflowDefinitionDraftConnectionIfMissing()
    {
        if (string.IsNullOrWhiteSpace(SelectedWorkflowDefinitionDraftConnectionId))
        {
            return;
        }

        if (WorkflowDefinitionDraftStructure?.Connections.Any(connection =>
            string.Equals(
                connection.ConnectionId,
                SelectedWorkflowDefinitionDraftConnectionId,
                StringComparison.Ordinal)) == true)
        {
            return;
        }

        SelectedWorkflowDefinitionDraftConnectionId = string.Empty;
    }

    private static string FormatRelatedConnectionSummary(
        WorkflowDefinitionDraftConnection connection)
    {
        var connectionId = string.IsNullOrWhiteSpace(connection.ConnectionId)
            ? "?"
            : connection.ConnectionId;

        return
            $"- {connectionId}: {FormatConnectionEndpoint(connection.SourceNodeId, connection.SourcePort)} -> {FormatConnectionEndpoint(connection.TargetNodeId, connection.TargetPort)}";
    }

    private static string FormatConnectionEndpoint(string nodeId, string port)
    {
        if (string.IsNullOrWhiteSpace(nodeId))
        {
            return string.IsNullOrWhiteSpace(port) ? "?" : port;
        }

        return string.IsNullOrWhiteSpace(port)
            ? nodeId
            : $"{nodeId}.{port}";
    }

    partial void OnNewDraftConnectionIdChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftConnectionSourceNodeIdChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftConnectionSourcePortChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftConnectionTargetNodeIdChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftConnectionTargetPortChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedWorkflowDefinitionDraftConnectionIdChanged(string value)
    {
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsWorkflowConnectionsAdvancedVisibleChanged(bool value)
    {
        OnPropertyChanged(nameof(ShowConnectionsText));
    }
}
