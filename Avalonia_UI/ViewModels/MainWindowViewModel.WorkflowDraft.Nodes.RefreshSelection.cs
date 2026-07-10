using System;
using System.Linq;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RestoreWorkflowDefinitionDraftNodeSelection()
    {
        var selectedNodeId = workflowNodeSelectionState.ResolveSelectedNodeId(
            WorkflowDefinitionDraftNodes
                .Select(node => node.NodeInstanceId)
                .ToArray());
        SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault(node =>
            string.Equals(node.NodeInstanceId, selectedNodeId, StringComparison.Ordinal));
    }
}
