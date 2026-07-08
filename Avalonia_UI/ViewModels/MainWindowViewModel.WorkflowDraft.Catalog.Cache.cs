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

    private string? PrepareNodeConfigSchemaCache(
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState)
    {
        var catalogKey = nodeDefinitionCatalogCacheState.PrepareSchemaCatalogKey(
            connectionKey,
            catalogState,
            out var changed);
        if (changed)
        {
            nodeConfigSchemaByKey.Clear();
        }

        return catalogKey;
    }

    private NodeConfigSchemaParseResult GetOrParseNodeConfigSchema(
        NodeDefinitionDto definition,
        string? schemaCatalogKey)
    {
        if (schemaCatalogKey is null)
        {
            return NodeConfigSchemaParser.Parse(
                definition.ConfigSchemaVersion,
                definition.ConfigSchema);
        }

        var schemaCacheKey = NodeDefinitionCatalogCacheState.BuildSchemaCacheKey(definition);
        if (nodeConfigSchemaByKey.TryGetValue(schemaCacheKey, out var cached))
        {
            return cached;
        }

        var parsed = NodeConfigSchemaParser.Parse(
            definition.ConfigSchemaVersion,
            definition.ConfigSchema);
        nodeConfigSchemaByKey[schemaCacheKey] = parsed;
        return parsed;
    }

}
