namespace Avalonia_UI.ViewModels;

public sealed record SqliteTableOptionViewModel(
    string? TableName,
    string DisplayText,
    bool IsAllTables = false);
