using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RefreshWorkflowDefinitionDraftStructureState()
    {
        WorkflowDefinitionDraftStructure =
            ReadWorkflowDefinitionDraftStructureFromCache();
        RefreshWorkflowDefinitionDraftNodes();
        ClearSelectedWorkflowDefinitionDraftNodeIfMissing();
        ClearSelectedWorkflowDefinitionDraftConnectionIfMissing();
        ClearSelectedNewDraftConnectionNodesIfMissing();
    }

    public string WorkflowLinearChainStatusText
    {
        get
        {
            if (string.IsNullOrWhiteSpace(WorkflowDefinitionDraftJson))
            {
                return T("definition.linear_chain_status_not_loaded");
            }

            var analysis = ReadWorkflowDefinitionLinearChainAnalysisFromCache();
            if (analysis is null)
            {
                return T("definition.linear_chain_status_not_loaded");
            }

            return analysis.IsLinear
                ? F(
                    "definition.linear_chain_status_linear",
                    analysis.NodeInstanceIds.Count)
                : F(
                    "definition.linear_chain_status_not_linear",
                    LocalizeWorkflowDefinitionDraftWarning(analysis.Warning));
        }
    }

    partial void OnWorkflowDefinitionDraftStructureChanged(
        WorkflowDefinitionDraftStructure? value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraftStructure));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftConnectionCount));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftConnectionCountText));
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraftStructureWarnings));
        if (SelectedRuntimeOptionsNode is not null &&
            !WorkflowDefinitionDraftNodes.Contains(SelectedRuntimeOptionsNode))
        {
            SelectedRuntimeOptionsNode = null;
        }

        NotifyWorkflowDefinitionNodeActionCommandsChanged();
    }
}
