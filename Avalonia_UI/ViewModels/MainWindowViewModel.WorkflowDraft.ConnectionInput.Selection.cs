using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplySelectedNewDraftConnectionSourceNode(
        WorkflowDefinitionDraftNode node)
    {
        NewDraftConnectionSourceNodeId = node.NodeInstanceId;
        ApplySuggestedNewDraftConnectionId();
    }

    private void ApplySelectedNewDraftConnectionTargetNode(
        WorkflowDefinitionDraftNode node)
    {
        NewDraftConnectionTargetNodeId = node.NodeInstanceId;
        ApplySuggestedNewDraftConnectionId();
    }

    partial void OnSelectedNewDraftConnectionSourceNodeChanged(
        WorkflowDefinitionDraftNode? value)
    {
        if (value is not null)
        {
            ApplySelectedNewDraftConnectionSourceNode(value);
        }
    }

    partial void OnSelectedNewDraftConnectionTargetNodeChanged(
        WorkflowDefinitionDraftNode? value)
    {
        if (value is not null)
        {
            ApplySelectedNewDraftConnectionTargetNode(value);
        }
    }
}
