using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void AddLoadedNodeDefinitionItems(
        IEnumerable<NodeDefinitionDto> definitions,
        string? schemaCatalogKey)
    {
        foreach (var definition in definitions
            .OrderBy(definition => definition.DisplayName)
            .ThenBy(definition => definition.NodeType)
            .ThenBy(definition => definition.NodeVersion))
        {
            var item = new NodeDefinitionListItemViewModel(
                definition,
                DisplayTextFormatter,
                GetOrParseNodeConfigSchema(definition, schemaCatalogKey));
            NodeDefinitions.Add(item);
            nodeDefinitionByKey[NodeDefinitionCatalogCacheState.BuildLookupKey(
                    item.NodeType,
                    item.NodeVersion)] =
                item;
        }
    }
}
