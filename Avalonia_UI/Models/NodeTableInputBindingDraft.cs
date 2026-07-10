namespace Avalonia_UI.Models;

public sealed record NodeTableInputBindingDraft
{
    public const string CurrentSourceType = "current";
    public const string UpstreamTableSourceType = "upstream_table";

    public string Slot { get; init; } = "in";

    public string Type { get; init; } = CurrentSourceType;

    public string? SourceNodeInstanceId { get; init; }

    public string? OutputSlot { get; init; }

    public string? OutputRole { get; init; }

    public string? StorageKind { get; init; }

    public string? LogicalTableId { get; init; }

    public bool IsCurrent => Type == CurrentSourceType;

    public bool IsUpstreamTable => Type == UpstreamTableSourceType;
}
