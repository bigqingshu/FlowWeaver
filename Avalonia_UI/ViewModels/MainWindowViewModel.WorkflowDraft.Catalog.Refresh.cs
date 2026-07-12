using System.Threading.Tasks;
using System.Collections.Generic;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task RefreshNodeDefinitionsCoreAsync(bool allowStateCacheHit)
    {
        var requestVersion = BeginNodeDefinitionsRefresh();
        var settings = BuildSettings();
        var connectionKey = NodeDefinitionCatalogCacheState.BuildConnectionKey(settings);

        try
        {
            var catalogStateTask = TryGetNodeDefinitionCatalogStateAsync(settings);
            var pluginCatalogStateTask = TryGetPluginCatalogStateAsync(settings);
            await Task.WhenAll(catalogStateTask, pluginCatalogStateTask);
            var catalogState = await catalogStateTask;
            var pluginCatalogState = await pluginCatalogStateTask;
            if (requestVersion != nodeDefinitionsLoadVersion)
            {
                return;
            }

            if (allowStateCacheHit
                && nodeDefinitionCatalogCacheState.IsCatalogHit(
                    connectionKey,
                    catalogState,
                    pluginCatalogState))
            {
                ApplyNodeDefinitionsCatalogCacheHit();
                return;
            }

            var responseTask = _apiClient.ListNodeDefinitionsAsync(
                settings,
                _shutdown.Token);
            var pluginResponseTask = TryListPluginsAsync(settings);
            await Task.WhenAll(responseTask, pluginResponseTask);
            var response = await responseTask;
            var pluginResponse = await pluginResponseTask;

            if (requestVersion != nodeDefinitionsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                var plugins = pluginResponse is { Ok: true, Data: not null }
                    ? pluginResponse.Data
                    : new List<PluginCatalogEntryDto>();
                ApplyLoadedNodeDefinitions(
                    response.Data,
                    plugins,
                    connectionKey,
                    catalogState,
                    pluginResponse is null || pluginResponse.Ok
                        ? pluginCatalogState
                        : null);
                if (pluginResponse is { Ok: false })
                {
                    NodeDefinitionCatalogErrorMessage = DescribeError(pluginResponse);
                }
                return;
            }

            ApplyNodeDefinitionsRefreshFailure(response);
        }
        finally
        {
            CompleteNodeDefinitionsRefresh(requestVersion);
        }
    }
}
