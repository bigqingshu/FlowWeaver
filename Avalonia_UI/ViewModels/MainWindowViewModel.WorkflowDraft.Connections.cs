using System;
using System.Linq;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isWorkflowConnectionsAdvancedVisible;

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
}
