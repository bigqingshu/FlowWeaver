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

    public string FormatConfigSchemaUnavailable()
    {
        return Text("node_catalog.config_schema_unavailable");
    }

    public string FormatNoConfigFields()
    {
        return Text("node_catalog.no_config_fields");
    }

    public string FormatConfigFields(int count, string fieldNames)
    {
        return Format("format.config_fields", count, fieldNames);
    }

    public string FormatNodeDefinitionDisplayName(
        string nodeType,
        string fallbackDisplayName)
    {
        var fallback = string.IsNullOrWhiteSpace(fallbackDisplayName)
            ? nodeType
            : fallbackDisplayName;
        if (string.IsNullOrWhiteSpace(nodeType))
        {
            return fallback;
        }

        return TextOrFallback($"node_definition.{nodeType}.display_name", fallback);
    }

    public string FormatNodeConfigFieldTitle(
        string nodeType,
        string fieldName,
        string? fallbackTitle)
    {
        var fallback = string.IsNullOrWhiteSpace(fallbackTitle)
            ? fieldName
            : fallbackTitle;
        if (string.IsNullOrWhiteSpace(nodeType) || string.IsNullOrWhiteSpace(fieldName))
        {
            return fallback;
        }

        return TextOrFallback($"node_config.{nodeType}.{fieldName}.title", fallback);
    }

    public string FormatNodeConfigFieldType(string typeName)
    {
        if (string.IsNullOrWhiteSpace(typeName))
        {
            return typeName;
        }

        return TextOrFallback(
            $"node_config.type.{typeName.ToLowerInvariant()}",
            typeName);
    }

    public string FormatSelectedNodeConfigDraftMissingSelection()
    {
        return Text("node_config_draft.no_node_selected");
    }

    public string FormatSelectedNodeConfigDraftSchemaUnavailable()
    {
        return Text("node_config_draft.schema_unavailable");
    }

    public string FormatSelectedNodeConfigDraftReady(
        string nodeInstanceId,
        int editableCount,
        int fallbackCount)
    {
        return Format(
            "format.node_config_draft_ready",
            nodeInstanceId,
            editableCount,
            fallbackCount);
    }

    private string Text(string key)
    {
        return _localizationService?.GetString(key) ?? GetFallbackString(key);
    }

    private string TextOrFallback(string key, string fallback)
    {
        var text = Text(key);
        return string.Equals(text, key, System.StringComparison.Ordinal)
            ? fallback
            : text;
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
            "node_catalog.config_schema_unavailable" => "Config schema unavailable",
            "node_catalog.no_config_fields" => "No config fields",
            "node_config.type.string" => "String",
            "node_config.type.integer" => "Integer",
            "node_config.type.number" => "Number",
            "node_config.type.boolean" => "Boolean",
            "node_config.type.enum" => "Enum",
            "node_config.type.array" => "Array",
            "node_config.type.object" => "Object",
            "node_config.type.unsupported" => "Unsupported",
            "format.config_fields" => "{0} config field(s): {1}",
            "node_config_draft.no_node_selected" => "Select a node to inspect config draft.",
            "node_config_draft.schema_unavailable" => "Selected node config schema unavailable.",
            "format.node_config_draft_ready" =>
                "{0}: {1} editable config field(s), {2} JSON fallback field(s)",
            _ => key,
        };
    }
}
