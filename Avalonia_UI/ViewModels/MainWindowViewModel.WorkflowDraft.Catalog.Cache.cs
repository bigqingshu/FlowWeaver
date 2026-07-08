using System;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task<NodeDefinitionCatalogStateDto?> TryGetNodeDefinitionCatalogStateAsync(
        EngineHostConnectionSettings settings)
    {
        try
        {
            var response = await _apiClient.GetNodeDefinitionCatalogStateAsync(
                settings,
                _shutdown.Token);
            if (response.Ok
                && response.Data is { } state
                && !string.IsNullOrWhiteSpace(state.CatalogHash))
            {
                return state;
            }
        }
        catch (NotSupportedException)
        {
        }

        return null;
    }

    private void InvalidateNodeDefinitionCatalogCacheState()
    {
        nodeDefinitionCatalogCacheState.InvalidateCatalog();
    }

}
