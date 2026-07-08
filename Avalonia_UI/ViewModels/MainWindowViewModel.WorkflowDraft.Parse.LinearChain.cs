using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private WorkflowDefinitionLinearChainAnalysis?
        ReadWorkflowDefinitionLinearChainAnalysisFromCache()
    {
        return workflowDefinitionDraftParseCache.GetLinearChainAnalysis(
            WorkflowDefinitionDraftJson);
    }
}
