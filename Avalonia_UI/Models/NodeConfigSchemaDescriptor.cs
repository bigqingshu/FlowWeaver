using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record NodeConfigSchemaDescriptor
{
    public string Version { get; init; } = string.Empty;

    public string Type { get; init; } = string.Empty;

    public IReadOnlyList<NodeConfigFieldDescriptor> Fields { get; init; } = [];

    public IReadOnlyList<string> Warnings { get; init; } = [];

    public bool IsSupported { get; init; }
}
