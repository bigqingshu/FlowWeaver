namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyNodeDefinitionsCatalogCacheHit()
    {
        NodeDefinitionCatalogMessage =
            F("format.loaded_node_definitions", NodeDefinitions.Count);
        OnPropertyChanged(nameof(HasNodeDefinitions));
        OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
    }
}
