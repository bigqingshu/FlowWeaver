using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private readonly WorkflowDefinitionDraftParseCache workflowDefinitionDraftParseCache = new();

    private WorkflowDefinitionDraftStructure? ReadWorkflowDefinitionDraftStructureFromCache()
    {
        return workflowDefinitionDraftParseCache.GetStructure(
            WorkflowDefinitionDraftJson,
            DisplayTextFormatter);
    }

    private void InvalidateWorkflowDefinitionDraftParseCache()
    {
        workflowDefinitionDraftParseCache.Invalidate();
    }
}
