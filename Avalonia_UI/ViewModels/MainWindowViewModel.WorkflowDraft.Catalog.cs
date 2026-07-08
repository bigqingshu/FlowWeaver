using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

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
}
