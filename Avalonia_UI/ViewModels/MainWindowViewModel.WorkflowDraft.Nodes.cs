using System;
using System.Linq;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RefreshWorkflowDefinitionDraftNodes()
    {
        var selectedNodeId = SelectedWorkflowDefinitionNode?.NodeInstanceId;
        workflowNodeSelectionState.Capture(
            selectedNodeId,
            !string.IsNullOrWhiteSpace(selectedNodeId));
        var batchSelectedNodeIds = WorkflowDefinitionDraftNodes
            .Where(node => node.IsBatchSelected)
            .Select(node => node.NodeInstanceId)
            .ToHashSet(StringComparer.Ordinal);

        RebuildWorkflowDefinitionDraftNodeItems(batchSelectedNodeIds);

        RestoreWorkflowDefinitionDraftNodeSelection();
        NotifyWorkflowDefinitionDraftNodeListPresentationChanged();
        RefreshWorkflowDefinitionBatchSelectionState();
    }
}
