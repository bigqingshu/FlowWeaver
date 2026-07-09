namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshNodeDefinitions()
    {
        return CanUseEngineActions && !IsLoadingNodeDefinitions;
    }
}
