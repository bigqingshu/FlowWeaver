using System;
using System.Globalization;
using System.Text.Json;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

internal static class RunDiagnosticValueFormatter
{
    private static readonly JsonSerializerOptions DisplayJsonOptions = new(FlowWeaverJson.Options)
    {
        WriteIndented = true,
    };

    public static string FormatOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? "-" : value;
    }

    public static string FormatTimestamp(DateTimeOffset? value)
    {
        return value?.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss") ?? "-";
    }

    public static string FormatDuration(
        DateTimeOffset? startedAt,
        DateTimeOffset? finishedAt)
    {
        if (startedAt is null)
        {
            return "-";
        }

        var duration = (finishedAt ?? DateTimeOffset.Now) - startedAt.Value;
        if (duration < TimeSpan.Zero)
        {
            return "-";
        }

        return duration.TotalHours >= 1
            ? duration.ToString(@"hh\:mm\:ss", CultureInfo.CurrentCulture)
            : duration.ToString(@"mm\:ss", CultureInfo.CurrentCulture);
    }

    public static string FormatJson(JsonElement? value)
    {
        return value is null
            || value.Value.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined
            ? string.Empty
            : JsonSerializer.Serialize(value.Value, DisplayJsonOptions);
    }
}
