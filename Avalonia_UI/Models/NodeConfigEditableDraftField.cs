using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record NodeConfigEditableDraftField
{
    public string Name { get; init; } = string.Empty;

    public NodeConfigFieldType Type { get; init; } = NodeConfigFieldType.Unsupported;

    public string? Title { get; init; }

    public bool Required { get; init; }

    public string InputValue { get; init; } = string.Empty;

    public IReadOnlyList<string> EnumValues { get; init; } = [];

    public IReadOnlyList<string> Warnings { get; init; } = [];
}
