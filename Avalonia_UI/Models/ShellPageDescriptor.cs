namespace Avalonia_UI.Models;

public sealed record ShellPageDescriptor(
    ShellPageKey Key,
    ShellPageContentKey ContentKey,
    int SortOrder,
    string HeaderPropertyName,
    string ViewTypeName,
    bool IsVisible = true,
    bool IsEnabled = true);
