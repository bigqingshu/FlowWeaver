using System.Collections.Generic;

namespace Avalonia_UI.Models;

public static class BuiltinNodeEditors
{
    public static IReadOnlyList<NodeEditorDescriptor> All { get; } =
        [];

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
