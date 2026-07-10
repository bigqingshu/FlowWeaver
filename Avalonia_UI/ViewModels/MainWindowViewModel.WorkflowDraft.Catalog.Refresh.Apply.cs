using System.Collections.Generic;
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
        AddLoadedNodeDefinitionItems(definitions, schemaCatalogKey);

        nodeDefinitionCatalogCacheState.RecordLoadedCatalog(connectionKey, catalogState);
        RefreshNodeEditorSchemaFallbackNodes();
        NotifyNodeDefinitionCatalogPresentationStateChanged();
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshSelectedNodeConfigDraftState();
        UpdateWorkflowNodeTableBindingsNodeCatalog(catalogState?.CatalogHash);
        NodeDefinitionCatalogMessage =
            F("format.loaded_node_definitions", NodeDefinitions.Count);
    }
}
