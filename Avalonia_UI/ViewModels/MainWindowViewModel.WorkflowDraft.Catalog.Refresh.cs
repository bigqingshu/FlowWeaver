using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task RefreshNodeDefinitionsCoreAsync(bool allowStateCacheHit)
    {
        var requestVersion = ++nodeDefinitionsLoadVersion;
        IsLoadingNodeDefinitions = true;
        NodeDefinitionCatalogMessage = T("node_catalog.loading");
        NodeDefinitionCatalogErrorMessage = null;
        var settings = BuildSettings();
        var connectionKey = NodeDefinitionCatalogCacheState.BuildConnectionKey(settings);

        try
        {
            var catalogState = await TryGetNodeDefinitionCatalogStateAsync(settings);
            if (requestVersion != nodeDefinitionsLoadVersion)
            {
                return;
            }

            if (allowStateCacheHit
                && nodeDefinitionCatalogCacheState.IsCatalogHit(connectionKey, catalogState))
            {
                ApplyNodeDefinitionsCatalogCacheHit();
                return;
            }

            var response = await _apiClient.ListNodeDefinitionsAsync(
                settings,
                _shutdown.Token);

            if (requestVersion != nodeDefinitionsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                ApplyLoadedNodeDefinitions(response.Data, connectionKey, catalogState);
                return;
            }

            ApplyNodeDefinitionsRefreshFailure(response);
        }
        finally
        {
            if (requestVersion == nodeDefinitionsLoadVersion)
            {
                IsLoadingNodeDefinitions = false;
            }
        }
    }

    private async Task RefreshNodeDefinitionsAfterHealthyConnectionAsync()
    {
        if (!CanRefreshNodeDefinitions())
        {
            return;
        }

        await RefreshNodeDefinitionsCoreAsync(allowStateCacheHit: true);
    }
}
