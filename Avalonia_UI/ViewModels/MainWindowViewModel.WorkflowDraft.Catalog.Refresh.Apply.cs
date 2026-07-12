using System.Collections.Generic;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyLoadedNodeDefinitions(
        IReadOnlyCollection<NodeDefinitionDto> definitions,
        IReadOnlyCollection<PluginCatalogEntryDto> plugins,
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState,
        PluginCatalogStateDto? pluginCatalogState)
    {
        SelectedNewDraftNodeDefinition = null;
        NodeDefinitions.Clear();
        AddableNodeDefinitions.Clear();
        nodeDefinitionByKey.Clear();
        var schemaCatalogKey = PrepareNodeConfigSchemaCache(
            connectionKey,
            catalogState);
        AddLoadedNodeDefinitionItems(definitions, plugins, schemaCatalogKey);

        nodeDefinitionCatalogCacheState.RecordLoadedCatalog(
            connectionKey,
            catalogState,
            pluginCatalogState);
        RefreshNodeEditorSchemaFallbackNodes();
        NotifyNodeDefinitionCatalogPresentationStateChanged();
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshSelectedNodeConfigDraftState();
        UpdateWorkflowNodeTableBindingsNodeCatalog(catalogState?.CatalogHash);
        NodeDefinitionCatalogMessage =
            F("format.loaded_node_definitions", NodeDefinitions.Count);
    }
}
