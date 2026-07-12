using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task<PluginCatalogStateDto?> TryGetPluginCatalogStateAsync(
        EngineHostConnectionSettings settings)
    {
        try
        {
            var response = await _apiClient.GetPluginCatalogStateAsync(
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

    private async Task<ApiResponseEnvelope<List<PluginCatalogEntryDto>>?> TryListPluginsAsync(
        EngineHostConnectionSettings settings)
    {
        try
        {
            return await _apiClient.ListPluginsAsync(settings, _shutdown.Token);
        }
        catch (NotSupportedException)
        {
            return null;
        }
    }
}
