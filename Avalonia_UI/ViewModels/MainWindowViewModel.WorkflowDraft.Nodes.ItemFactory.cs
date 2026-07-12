using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private WorkflowDefinitionNodeListItemViewModel CreateWorkflowDefinitionDraftNodeListItem(
        WorkflowDefinitionDraftNode node,
        int displayOrder,
        bool isBatchSelected)
    {
        return new WorkflowDefinitionNodeListItemViewModel(
            node.NodeInstanceId,
            node.NodeType,
            node.NodeVersion,
            node.DisplayName,
            node.Enabled,
            node.ConfigJson,
            DisplayTextFormatter,
            _nodeEditorResolver.Resolve(node.NodeType, node.DisplayName, node.NodeVersion),
            displayOrder)
        {
            IsBatchSelected = isBatchSelected,
        };
    }
}
