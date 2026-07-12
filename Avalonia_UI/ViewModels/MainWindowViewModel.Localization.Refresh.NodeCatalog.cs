namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyNodeCatalogLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(NodeCatalogSectionText));
        OnPropertyChanged(nameof(NodeText));
        OnPropertyChanged(nameof(NodeCatalogEmptyStateText));
        OnPropertyChanged(nameof(InputsText));
        OnPropertyChanged(nameof(OutputsText));
        OnPropertyChanged(nameof(NodeCatalogSourceText));
        OnPropertyChanged(nameof(ModeText));
        OnPropertyChanged(nameof(TimeoutText));
    }
}
