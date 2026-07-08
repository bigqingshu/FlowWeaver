using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int nodeDefinitionsLoadVersion;
    private readonly NodeDefinitionCatalogCacheState nodeDefinitionCatalogCacheState = new();
    private readonly Dictionary<(string NodeType, string NodeVersion), NodeDefinitionListItemViewModel>
        nodeDefinitionByKey = new();
    private readonly Dictionary<string, NodeConfigSchemaParseResult> nodeConfigSchemaByKey =
        new(StringComparer.Ordinal);

    [ObservableProperty]
    private bool isLoadingNodeDefinitions;

    [ObservableProperty]
    private string nodeDefinitionCatalogMessage = "No node definitions loaded.";

    [ObservableProperty]
    private string? nodeDefinitionCatalogErrorMessage;

    public ObservableCollection<NodeDefinitionListItemViewModel> NodeDefinitions { get; } =
        new();

    public bool HasNodeDefinitionCatalogError =>
        !string.IsNullOrWhiteSpace(NodeDefinitionCatalogErrorMessage);

    public bool HasNodeDefinitions => NodeDefinitions.Count > 0;

    public bool HasNodeDefinitionCatalogEmptyState =>
        !IsLoadingNodeDefinitions && !HasNodeDefinitions;

    public string? RefreshNodeDefinitionsDisabledReasonText
    {
        get
        {
            if (IsLoadingNodeDefinitions)
            {
                return T("action.disabled.busy");
            }

            if (!CanUseEngineActions)
            {
                return T("action.disabled.engine_not_connected");
            }

            return null;
        }
    }

    public string NodeCatalogSectionText => T("node_catalog.section");

    public string NodeText => T("node_catalog.node");

    public string NodeCatalogEmptyStateText => T("node_catalog.empty_state");

    public string InputsText => T("node_catalog.inputs");

    public string OutputsText => T("node_catalog.outputs");

    public string ModeText => T("node_catalog.mode");

    public string TimeoutText => T("node_catalog.timeout");

    private bool CanRefreshNodeDefinitions()
    {
        return CanUseEngineActions && !IsLoadingNodeDefinitions;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshNodeDefinitions))]
    private async Task RefreshNodeDefinitionsAsync()
    {
        await RefreshNodeDefinitionsCoreAsync(allowStateCacheHit: false);
    }

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

    partial void OnIsLoadingNodeDefinitionsChanged(bool value)
    {
        OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
        RefreshNodeDefinitionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnNodeDefinitionCatalogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasNodeDefinitionCatalogError));
    }
}
