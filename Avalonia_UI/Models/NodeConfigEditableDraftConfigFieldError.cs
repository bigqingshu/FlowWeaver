namespace Avalonia_UI.Models;

public sealed record NodeConfigEditableDraftConfigFieldError
{
    public string FieldName { get; init; } = string.Empty;

    public string Warning { get; init; } = string.Empty;
}
