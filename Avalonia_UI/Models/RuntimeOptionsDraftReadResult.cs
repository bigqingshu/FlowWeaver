namespace Avalonia_UI.Models;

public sealed record RuntimeOptionsDraftReadResult
{
    public RuntimeOptionsDraftReadStatus Status { get; init; }

    public RuntimeOptionsDraft Draft { get; init; } = new();

    public string? Warning { get; init; }

    public bool Succeeded => Status == RuntimeOptionsDraftReadStatus.Succeeded;
}
