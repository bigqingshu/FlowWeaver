using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record NodeConfigDraft
{
    public string NodeInstanceId { get; init; } = string.Empty;

    public NodeConfigDraftStatus Status { get; init; } =
        NodeConfigDraftStatus.SchemaUnsupported;

    public IReadOnlyList<NodeConfigDraftField> Fields { get; init; } = [];

    public IReadOnlyList<string> Warnings { get; init; } = [];

    public bool IsSupported => Status == NodeConfigDraftStatus.Supported;
}
