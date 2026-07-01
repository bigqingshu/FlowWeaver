namespace Avalonia_UI.Models;

public sealed record ShellPageDescriptor(
    ShellPageKey Key,
    int SortOrder,
    string HeaderPropertyName,
    string ViewTypeName,
    bool IsVisible = true,
    bool IsEnabled = true);
