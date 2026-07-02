using System.Collections.Generic;
using System.Text.Json;

namespace Avalonia_UI.Models;

public sealed record NodeConfigDraftField
{
    public string Name { get; init; } = string.Empty;

    public NodeConfigFieldType Type { get; init; } = NodeConfigFieldType.Unsupported;

    public string? Title { get; init; }

    public bool Required { get; init; }

    public JsonElement? CurrentValue { get; init; }

    public JsonElement? DefaultValue { get; init; }

    public bool HasCurrentValue => CurrentValue.HasValue;

    public bool IsEditable { get; init; }

    public IReadOnlyList<string> Warnings { get; init; } = [];
}
