using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private WorkflowDefinitionDraftStructure? ReadWorkflowDefinitionDraftStructureFromCache()
    {
        return workflowDefinitionDraftParseCache.GetStructure(
            WorkflowDefinitionDraftJson,
            DisplayTextFormatter);
    }
}
