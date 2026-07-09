using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private readonly WorkflowDefinitionDraftParseCache workflowDefinitionDraftParseCache = new();

    private void InvalidateWorkflowDefinitionDraftParseCache()
    {
        workflowDefinitionDraftParseCache.Invalidate();
    }
}
