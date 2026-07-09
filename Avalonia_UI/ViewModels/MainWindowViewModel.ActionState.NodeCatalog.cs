namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyNodeCatalogSummaryActionStateChanged()
    {
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
    }
}
