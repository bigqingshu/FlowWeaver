using System;
using System.Linq;

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
                var nodeItem = CreateWorkflowDefinitionDraftNodeListItem(
                    node,
                    displayOrder,
                    batchSelectedNodeIds.Contains(node.NodeInstanceId));
                nodeItem.PropertyChanged += OnWorkflowDefinitionDraftNodeItemPropertyChanged;
                WorkflowDefinitionDraftNodes.Add(nodeItem);
                displayOrder++;
            }
        }

        RestoreWorkflowDefinitionDraftNodeSelection(
            selectedNodeId,
            hadSelectedNode);
        NotifyWorkflowDefinitionDraftNodeListPresentationChanged();
        RefreshWorkflowDefinitionBatchSelectionState();
    }
}
