namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnIsLoadingNodeDefinitionsChanged(bool value)
    {
        OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
        RefreshNodeDefinitionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnNodeDefinitionCatalogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasNodeDefinitionCatalogError));
    }
}
