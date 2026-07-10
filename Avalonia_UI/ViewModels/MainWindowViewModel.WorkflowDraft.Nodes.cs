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

        RebuildWorkflowDefinitionDraftNodeItems(batchSelectedNodeIds);

        RestoreWorkflowDefinitionDraftNodeSelection(
            selectedNodeId,
            hadSelectedNode);
        NotifyWorkflowDefinitionDraftNodeListPresentationChanged();
        RefreshWorkflowDefinitionBatchSelectionState();
    }
}
