using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task RefreshNodeDefinitionsCoreAsync(bool allowStateCacheHit)
    {
        var requestVersion = ++nodeDefinitionsLoadVersion;
        IsLoadingNodeDefinitions = true;
        NodeDefinitionCatalogMessage = T("node_catalog.loading");
        NodeDefinitionCatalogErrorMessage = null;
        var settings = BuildSettings();
        var connectionKey = NodeDefinitionCatalogCacheState.BuildConnectionKey(settings);

        try
        {
            var catalogState = await TryGetNodeDefinitionCatalogStateAsync(settings);
            if (requestVersion != nodeDefinitionsLoadVersion)
            {
                return;
            }

            if (allowStateCacheHit
                && nodeDefinitionCatalogCacheState.IsCatalogHit(connectionKey, catalogState))
            {
                NodeDefinitionCatalogMessage =
                    F("format.loaded_node_definitions", NodeDefinitions.Count);
                OnPropertyChanged(nameof(HasNodeDefinitions));
                OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
                return;
            }

            var response = await _apiClient.ListNodeDefinitionsAsync(
                settings,
                _shutdown.Token);

            if (requestVersion != nodeDefinitionsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                SelectedNewDraftNodeDefinition = null;
                NodeDefinitions.Clear();
                nodeDefinitionByKey.Clear();
                var schemaCatalogKey = PrepareNodeConfigSchemaCache(
                    connectionKey,
                    catalogState);
                foreach (var definition in response.Data
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
                OnPropertyChanged(nameof(HasNodeDefinitions));
                OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
                RefreshWorkflowDefinitionDraftStructureState();
                RefreshSelectedNodeConfigDraftState();
                NodeDefinitionCatalogMessage =
                    F("format.loaded_node_definitions", NodeDefinitions.Count);
                return;
            }

            NodeDefinitionCatalogMessage = T("node_catalog.refresh_failed");
            NodeDefinitionCatalogErrorMessage = DescribeError(response);
            SelectedNewDraftNodeDefinition = null;
            OnPropertyChanged(nameof(HasNodeDefinitions));
            OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
            RefreshSelectedNodeConfigDraftState();
        }
        finally
        {
            if (requestVersion == nodeDefinitionsLoadVersion)
            {
                IsLoadingNodeDefinitions = false;
            }
        }
    }

    private async Task RefreshNodeDefinitionsAfterHealthyConnectionAsync()
    {
        if (!CanRefreshNodeDefinitions())
        {
            return;
        }

        await RefreshNodeDefinitionsCoreAsync(allowStateCacheHit: true);
    }
}
