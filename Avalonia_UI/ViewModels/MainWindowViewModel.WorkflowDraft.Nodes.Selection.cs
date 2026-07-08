using System;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void SelectWorkflowDefinitionDraftNode(string nodeInstanceId)
    {
        SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault(node =>
            string.Equals(
                node.NodeInstanceId,
                nodeInstanceId,
                StringComparison.Ordinal));
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
}
