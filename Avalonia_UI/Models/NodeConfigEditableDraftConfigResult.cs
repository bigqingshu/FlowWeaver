using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record NodeConfigEditableDraftConfigResult
{
    public NodeConfigEditableDraftConfigBuildStatus Status { get; init; }

    public string ConfigJson { get; init; } = "{}";

    public IReadOnlyList<NodeConfigEditableDraftConfigFieldError> FieldErrors { get; init; } = [];

    public IReadOnlyList<string> Warnings { get; init; } = [];

    public bool Succeeded => Status == NodeConfigEditableDraftConfigBuildStatus.Succeeded;
}
