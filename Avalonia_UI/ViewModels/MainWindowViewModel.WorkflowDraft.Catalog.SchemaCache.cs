using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
