using System.Globalization;

namespace Avalonia_UI.Localization;

public sealed class DisplayTextFormatter
{
    public static DisplayTextFormatter Invariant { get; } = new();

    private readonly ILocalizationService? _localizationService;

    private DisplayTextFormatter()
    {
    }

    public DisplayTextFormatter(ILocalizationService localizationService)
    {
        _localizationService = localizationService;
    }

    public string FormatNodeCount(int count)
    {
        return Format("format.list_node_count", count);
    }

    public string FormatConnectionCount(int count)
    {
        return Format("format.list_connection_count", count);
    }

    public string FormatEnabled(bool enabled)
    {
        return Text(enabled ? "list.enabled" : "list.disabled");
    }

    public string FormatAttempt(int attempt)
    {
        return Format("format.list_attempt", attempt);
    }

    public string FormatMemberCount(int count)
    {
        return Format("format.list_member_count", count);
    }

    public string FormatNodeEditorStatus(string statusKey)
    {
        return Text(string.IsNullOrWhiteSpace(statusKey)
            ? "node_editor.status.unregistered_json_fallback"
            : statusKey);
    }

    private string Text(string key)
    {
        return _localizationService?.GetString(key) ?? GetFallbackString(key);
    }

    private string Format(string key, params object?[] args)
    {
        return _localizationService is null
            ? string.Format(CultureInfo.CurrentCulture, GetFallbackString(key), args)
            : _localizationService.Format(key, args);
    }

    private static string GetFallbackString(string key)
    {
        return key switch
        {
            "format.list_node_count" => "{0} node(s)",
            "format.list_connection_count" => "{0} connection(s)",
            "list.enabled" => "enabled",
            "list.disabled" => "disabled",
            "format.list_attempt" => "attempt {0}",
            "format.list_member_count" => "{0} member(s)",
            "node_editor.status.builtin" => "Built-in editor",
            "node_editor.status.json_fallback" => "JSON fallback",
            "node_editor.status.unregistered_json_fallback" => "Not registered, JSON fallback",
            _ => key,
        };
    }
}
