using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record NodeConfigSchemaParseResult
{
    public NodeConfigSchemaDescriptor? Schema { get; init; }

    public IReadOnlyList<string> Warnings { get; init; } = [];

    public bool IsSupported => Schema?.IsSupported == true;
}
