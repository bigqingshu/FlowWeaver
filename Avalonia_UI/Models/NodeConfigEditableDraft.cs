using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record NodeConfigEditableDraft
{
    public string NodeInstanceId { get; init; } = string.Empty;

    public IReadOnlyList<NodeConfigEditableDraftField> Fields { get; init; } = [];

    public IReadOnlyList<string> Warnings { get; init; } = [];

    public bool HasFields => Fields.Count > 0;
}
