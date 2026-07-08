using System;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
