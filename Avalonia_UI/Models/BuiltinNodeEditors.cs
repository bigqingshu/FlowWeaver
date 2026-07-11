using System.Collections.Generic;

namespace Avalonia_UI.Models;

public static class BuiltinNodeEditors
{
    public static IReadOnlyList<NodeEditorDescriptor> All { get; } =
        [
            new NodeEditorDescriptor(
                "PublishSharedTablesNode",
                "Publish Shared Tables",
                NodeEditorKind.BuiltIn,
                NodeEditorKey.PublishSharedTables),
            new NodeEditorDescriptor(
                "ReadSharedTablesNode",
                "Read Shared Tables",
                NodeEditorKind.BuiltIn,
                NodeEditorKey.ReadSharedTables),
        ];

    public static NodeEditorRegistry CreateRegistry()
    {
        var registry = new NodeEditorRegistry();
        foreach (var descriptor in All)
        {
            registry.Register(descriptor);
        }

        return registry;
    }
}
