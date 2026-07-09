using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyLoadedNodeDefinitions(
        IReadOnlyCollection<NodeDefinitionDto> definitions,
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState)
    {
        SelectedNewDraftNodeDefinition = null;
        NodeDefinitions.Clear();
        nodeDefinitionByKey.Clear();
        var schemaCatalogKey = PrepareNodeConfigSchemaCache(
            connectionKey,
            catalogState);
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

        nodeDefinitionCatalogCacheState.RecordLoadedCatalog(connectionKey, catalogState);
        RefreshNodeEditorSchemaFallbackNodes();
        NotifyNodeDefinitionCatalogPresentationStateChanged();
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshSelectedNodeConfigDraftState();
        NodeDefinitionCatalogMessage =
            F("format.loaded_node_definitions", NodeDefinitions.Count);
    }
}
