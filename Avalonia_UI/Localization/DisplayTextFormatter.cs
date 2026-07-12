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

    public string FormatVersionCount(int count)
    {
        return Format("format.list_version_count", count);
    }

    public string FormatNodeEditorStatus(string statusKey)
    {
        return Text(string.IsNullOrWhiteSpace(statusKey)
            ? "node_editor.status.unregistered_json_fallback"
            : statusKey);
    }

    public string FormatNodeCatalogSource(
        string providerType,
        string pluginId,
        string? pluginVersion)
    {
        if (string.Equals(providerType, "core", System.StringComparison.OrdinalIgnoreCase))
        {
            return Text("node_catalog.source.core");
        }

        var source = string.IsNullOrWhiteSpace(pluginId)
            ? Text("node_catalog.source.plugin_unknown")
            : pluginId;
        return string.IsNullOrWhiteSpace(pluginVersion)
            ? Format("format.node_catalog.source.plugin", source)
            : Format("format.node_catalog.source.plugin_version", source, pluginVersion);
    }

    public string FormatNodeCatalogStatus(bool enabled)
    {
        return Text(enabled
            ? "node_catalog.status.available"
            : "node_catalog.status.unavailable");
    }

    public string FormatNodeCatalogDisabledReason(string reason)
    {
        return string.IsNullOrWhiteSpace(reason)
            ? string.Empty
            : Format("format.node_catalog.disabled_reason", reason);
    }

    public string FormatUnavailableNodeReason(string reason)
    {
        return string.IsNullOrWhiteSpace(reason)
            ? Text("node_editor.status.unavailable_json_fallback")
            : Format("format.node_editor.unavailable_reason", reason);
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

    public string FormatNodeConfigArrayAddItem()
    {
        return Text("node_config.array.add_item");
    }

    public string FormatNodeConfigArrayRemoveItem()
    {
        return Text("node_config.array.remove_item");
    }

    public string FormatNodeConfigArrayMoveUp()
    {
        return Text("node_config.array.move_up");
    }

    public string FormatNodeConfigArrayMoveDown()
    {
        return Text("node_config.array.move_down");
    }

    public string FormatNodeConfigOptionValue(
        string nodeType,
        string fieldName,
        string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return value;
        }

        if (!string.IsNullOrWhiteSpace(nodeType)
            && !string.IsNullOrWhiteSpace(fieldName))
        {
            var fieldSpecificText = TextOrFallback(
                $"node_config.{nodeType}.{fieldName}.option.{value}",
                value);
            if (!string.Equals(fieldSpecificText, value, System.StringComparison.Ordinal))
            {
                return fieldSpecificText;
            }
        }

        return TextOrFallback($"node_config.option.{value}", value);
    }

    public string FormatRuntimeOptionsOptionValue(string group, string value)
    {
        if (string.IsNullOrWhiteSpace(group) || string.IsNullOrWhiteSpace(value))
        {
            return value;
        }

        return TextOrFallback($"runtime_options.{group}.option.{value}", value);
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
            "format.list_version_count" => "{0} version(s)",
            "node_editor.status.builtin" => "Built-in editor",
            "node_editor.status.json_fallback" => "JSON fallback",
            "node_editor.status.unregistered_json_fallback" => "Not registered, JSON fallback",
            "node_editor.status.unavailable_json_fallback" => "Definition unavailable, JSON fallback only",
            "format.node_editor.unavailable_reason" => "Unavailable: {0}",
            "node_catalog.source.core" => "Built-in",
            "node_catalog.source.plugin_unknown" => "Unknown plugin",
            "format.node_catalog.source.plugin" => "Plugin {0}",
            "format.node_catalog.source.plugin_version" => "Plugin {0} v{1}",
            "node_catalog.status.available" => "Available",
            "node_catalog.status.unavailable" => "Unavailable",
            "format.node_catalog.disabled_reason" => "Reason: {0}",
            "node_catalog.config_schema_unavailable" => "Config schema unavailable",
            "node_catalog.no_config_fields" => "No config fields",
            "node_config.type.string" => "String",
            "node_config.type.integer" => "Integer",
            "node_config.type.number" => "Number",
            "node_config.type.boolean" => "Boolean",
            "node_config.type.enum" => "Enum",
            "node_config.type.array" => "Array",
            "node_config.type.string_array" => "String array",
            "node_config.type.object" => "Object",
            "node_config.type.unsupported" => "Unsupported",
            "node_config.array.add_item" => "Add item",
            "node_config.array.remove_item" => "Remove item",
            "node_config.array.move_up" => "Move up",
            "node_config.array.move_down" => "Move down",
            "format.config_fields" => "{0} config field(s): {1}",
            "node_config_draft.no_node_selected" => "Select a node to inspect config draft.",
            "node_config_draft.schema_unavailable" => "Selected node config schema unavailable.",
            "format.node_config_draft_ready" =>
                "{0}: {1} editable config field(s), {2} JSON fallback field(s)",
            _ => key,
        };
    }
}
