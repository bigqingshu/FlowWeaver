using System.Linq;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string? GetWorkflowDefinitionNodeMutationDisabledReason()
    {
        if (IsWorkflowDefinitionDraftBusy)
        {
            return T("action.disabled.busy");
        }

        if (!CanUseEngineActions)
        {
            return T("action.disabled.engine_not_connected");
        }

        if (WorkflowDefinitionDetail is null || !HasWorkflowDefinitionDraft)
        {
            return T("action.disabled.no_workflow_definition");
        }

        if (HasWorkflowDefinitionRevisionConflict)
        {
            return T("action.disabled.revision_conflict");
        }

        return null;
    }

    private string? GetSelectedWorkflowDefinitionNodeMutationDisabledReason()
    {
        var commonReason = GetWorkflowDefinitionNodeMutationDisabledReason();
        if (commonReason is not null)
        {
            return commonReason;
        }

        if (SelectedWorkflowDefinitionNode is null)
        {
            return T("action.disabled.no_workflow_node_selected");
        }

        if (FindDraftNode(SelectedWorkflowDefinitionNode.NodeInstanceId) is null)
        {
            return T("action.disabled.workflow_node_missing");
        }

        return null;
    }

    private string? GetSelectedWorkflowDefinitionDraftNodesMutationDisabledReason()
    {
        var commonReason = GetWorkflowDefinitionNodeMutationDisabledReason();
        if (commonReason is not null)
        {
            return commonReason;
        }

        var selectedNodes = WorkflowDefinitionDraftNodes
            .Where(node => node.IsBatchSelected)
            .ToArray();
        if (selectedNodes.Length == 0)
        {
            return T("action.disabled.no_workflow_nodes_checked");
        }

        return selectedNodes.Any(node => FindDraftNode(node.NodeInstanceId) is null)
            ? T("action.disabled.workflow_node_missing")
            : null;
    }

    private string? GetMoveSelectedWorkflowDefinitionDraftNodeDisabledReason(int offset)
    {
        var selectedReason = GetSelectedWorkflowDefinitionNodeMutationDisabledReason();
        if (selectedReason is not null)
        {
            return selectedReason;
        }

        var index = WorkflowDefinitionDraftNodes.IndexOf(SelectedWorkflowDefinitionNode!);
        var targetIndex = index + offset;
        if (index < 0)
        {
            return T("action.disabled.workflow_node_missing");
        }

        if (targetIndex < 0)
        {
            return T("action.disabled.workflow_node_at_top");
        }

        return targetIndex >= WorkflowDefinitionDraftNodes.Count
            ? T("action.disabled.workflow_node_at_bottom")
            : null;
    }
}
