using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void AddLoadedNodeDefinitionItems(
        IEnumerable<NodeDefinitionDto> definitions,
        IReadOnlyCollection<PluginCatalogEntryDto> plugins,
        string? schemaCatalogKey)
    {
        var pluginByNodeKey = plugins
            .Where(plugin =>
                plugin.Enabled
                && !string.IsNullOrWhiteSpace(plugin.NodeType)
                && !string.IsNullOrWhiteSpace(plugin.NodeVersion))
            .GroupBy(plugin => NodeDefinitionCatalogCacheState.BuildLookupKey(
                plugin.NodeType!,
                plugin.NodeVersion!))
            .ToDictionary(group => group.Key, group => group.First());
        var loadedPluginPackages = new HashSet<string>(System.StringComparer.OrdinalIgnoreCase);

        foreach (var definition in definitions
            .OrderBy(definition => definition.DisplayName)
            .ThenBy(definition => definition.NodeType)
            .ThenBy(definition => definition.NodeVersion))
        {
            pluginByNodeKey.TryGetValue(
                NodeDefinitionCatalogCacheState.BuildLookupKey(
                    definition.NodeType,
                    definition.NodeVersion),
                out var plugin);
            if (plugin is not null
                && !string.Equals(
                    plugin.PluginId,
                    definition.PluginId,
                    System.StringComparison.Ordinal))
            {
                plugin = null;
            }

            var item = new NodeDefinitionListItemViewModel(
                definition,
                DisplayTextFormatter,
                GetOrParseNodeConfigSchema(definition, schemaCatalogKey),
                plugin);
            NodeDefinitions.Add(item);
            if (item.CanAdd)
            {
                AddableNodeDefinitions.Add(item);
            }

            if (plugin is not null)
            {
                loadedPluginPackages.Add(plugin.PackageName);
            }

            nodeDefinitionByKey[NodeDefinitionCatalogCacheState.BuildLookupKey(
                    item.NodeType,
                    item.NodeVersion)] =
                item;
        }

        foreach (var plugin in plugins
            .Where(plugin => !loadedPluginPackages.Contains(plugin.PackageName))
            .OrderBy(plugin => plugin.DisplayName ?? plugin.PackageName)
            .ThenBy(plugin => plugin.PackageName))
        {
            NodeDefinitions.Add(new NodeDefinitionListItemViewModel(
                plugin,
                DisplayTextFormatter));
        }
    }
}
