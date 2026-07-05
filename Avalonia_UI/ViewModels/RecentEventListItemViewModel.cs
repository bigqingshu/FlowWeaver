using System;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public sealed class RecentEventListItemViewModel
{
    public RecentEventListItemViewModel(
        string key,
        UiNotificationKind kind,
        string sourceText,
        string title,
        string message,
        DateTimeOffset timestamp)
    {
        Key = string.IsNullOrWhiteSpace(key) ? "default" : key.Trim();
        Kind = kind;
        SourceText = sourceText ?? string.Empty;
        Title = title ?? string.Empty;
        Message = message ?? string.Empty;
        Timestamp = timestamp;
    }

    public string Key { get; }

    public UiNotificationKind Kind { get; }

    public string KindText => Kind.ToString();

    public string SourceText { get; }

    public string Title { get; }

    public string Message { get; }

    public DateTimeOffset Timestamp { get; }

    public string TimestampText => Timestamp.ToLocalTime().ToString("HH:mm:ss");

    public bool HasMessage => !string.IsNullOrWhiteSpace(Message);
}
