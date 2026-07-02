using System.Collections.Generic;
using System.Text.Json;

namespace Avalonia_UI.Models;

public sealed record NodeConfigFieldDescriptor
{
    public string Name { get; init; } = string.Empty;

    public NodeConfigFieldType Type { get; init; } = NodeConfigFieldType.Unsupported;

    public string TypeName { get; init; } = string.Empty;

    public string? Title { get; init; }

    public bool Required { get; init; }

    public JsonElement? DefaultValue { get; init; }

    public double? Minimum { get; init; }

    public IReadOnlyList<string> EnumValues { get; init; } = [];

    public string? ItemType { get; init; }

    public string? Description { get; init; }

    public IReadOnlyList<string> Warnings { get; init; } = [];
}
