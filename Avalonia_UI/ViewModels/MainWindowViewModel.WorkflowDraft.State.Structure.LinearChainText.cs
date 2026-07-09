namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
