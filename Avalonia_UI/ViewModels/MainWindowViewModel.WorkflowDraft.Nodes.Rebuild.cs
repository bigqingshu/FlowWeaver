using System.Collections.Generic;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RebuildWorkflowDefinitionDraftNodeItems(
        IReadOnlySet<string> batchSelectedNodeIds)
    {
        foreach (var node in WorkflowDefinitionDraftNodes)
        {
            node.PropertyChanged -= OnWorkflowDefinitionDraftNodeItemPropertyChanged;
        }

        WorkflowDefinitionDraftNodes.Clear();

        if (WorkflowDefinitionDraftStructure is null)
        {
            return;
        }

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
}
