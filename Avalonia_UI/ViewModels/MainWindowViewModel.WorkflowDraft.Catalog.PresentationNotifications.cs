namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyNodeDefinitionCatalogPresentationStateChanged()
    {
        OnPropertyChanged(nameof(HasNodeDefinitions));
        OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
    }
}
