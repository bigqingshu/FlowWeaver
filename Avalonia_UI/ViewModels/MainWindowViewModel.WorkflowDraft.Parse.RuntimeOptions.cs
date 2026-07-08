using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private RuntimeOptionsDraftReadResult
        ReadWorkflowDefinitionDraftRuntimeOptionsFromCache()
    {
        return workflowDefinitionDraftParseCache.GetRuntimeOptions(
            WorkflowDefinitionDraftJson);
    }
}
