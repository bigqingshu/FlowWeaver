using System;
using System.Collections.Generic;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int nodeDefinitionsLoadVersion;
    private readonly NodeDefinitionCatalogCacheState nodeDefinitionCatalogCacheState = new();
    private readonly Dictionary<(string NodeType, string NodeVersion), NodeDefinitionListItemViewModel>
        nodeDefinitionByKey = new();
    private readonly Dictionary<string, NodeConfigSchemaParseResult> nodeConfigSchemaByKey =
        new(StringComparer.Ordinal);
}
