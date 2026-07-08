using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private NodeDefinitionListItemViewModel? FindNodeDefinition(
        WorkflowDefinitionNodeListItemViewModel node)
    {
        return nodeDefinitionByKey.TryGetValue(
            NodeDefinitionCatalogCacheState.BuildLookupKey(
                node.NodeType,
                node.NodeVersion),
            out var definition)
                ? definition
                : null;
    }

    private void RefreshNodeEditorSchemaFallbackNodes()
    {
        _nodeEditorResolver.ReplaceSchemaFallbackNodes(
            NodeDefinitions
                .Where(definition => definition.ConfigSchemaDescriptor?.IsSupported == true)
                .Select(definition => (
                    definition.NodeType,
                    string.IsNullOrWhiteSpace(definition.DisplayName)
                        ? definition.NodeType
                        : definition.DisplayName)));
    }
}
