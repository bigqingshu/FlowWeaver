using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task<bool> EnsureWorkflowDefinitionDraftSavedForRunAsync()
    {
        return !IsWorkflowDefinitionDraftDirty ||
            await TrySaveWorkflowDefinitionDraftAsync();
    }
}
