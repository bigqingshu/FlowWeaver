namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int BeginNodeDefinitionsRefresh()
    {
        var requestVersion = ++nodeDefinitionsLoadVersion;
        IsLoadingNodeDefinitions = true;
        NodeDefinitionCatalogMessage = T("node_catalog.loading");
        NodeDefinitionCatalogErrorMessage = null;
        return requestVersion;
    }

    private void CompleteNodeDefinitionsRefresh(int requestVersion)
    {
        if (requestVersion == nodeDefinitionsLoadVersion)
        {
            IsLoadingNodeDefinitions = false;
        }
    }
}
