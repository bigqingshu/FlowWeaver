using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public static class NodeSpecializedEditorFactory
{
    public static INodeSpecializedEditorViewModel? Create(
        NodeEditorKey editorKey,
        NodeSpecializedEditorContext context)
    {
        return editorKey switch
        {
            NodeEditorKey.SqlMappingTable =>
                SqlMappingTableNodeEditorViewModel.TryCreate(context),
            NodeEditorKey.PublishSharedTables =>
                PublishSharedTablesNodeEditorViewModel.TryCreate(context),
            NodeEditorKey.ReadSharedTables =>
                ReadSharedTablesNodeEditorViewModel.TryCreate(context),
            _ => null,
        };
    }
}
