using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public sealed class NodeDefinitionListItemViewModel : ViewModelBase
{
    public NodeDefinitionListItemViewModel(
        NodeDefinitionDto definition,
        DisplayTextFormatter? displayTextFormatter = null,
        NodeConfigSchemaParseResult? configSchema = null,
        PluginCatalogEntryDto? plugin = null)
    {
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        IsCatalogDefinition = true;
        NodeType = definition.NodeType;
        NodeVersion = definition.NodeVersion;
        PackageName = plugin?.PackageName ?? string.Empty;
        PluginId = definition.PluginId;
        PluginVersion = plugin?.PluginVersion;
        ProviderType = definition.ProviderType;
        Category = definition.Category;
        Enabled = definition.Enabled;
        DisabledReason = definition.DisabledReason;
        DisplayName = definition.DisplayName;
        InputPorts = definition.InputPorts;
        OutputPorts = definition.OutputPorts;
        InputTableSlots = definition.InputTableSlots;
        OutputTableSlots = definition.OutputTableSlots;
        ExecutionMode = definition.ExecutionMode;
        DefaultTimeoutSeconds = definition.DefaultTimeoutSeconds;
        RetrySafe = definition.RetrySafe;
        UiVisibility = definition.UiVisibility;
        ConfigSchema = configSchema ?? NodeConfigSchemaParser.Parse(
            definition.ConfigSchemaVersion,
            definition.ConfigSchema);
    }

    public NodeDefinitionListItemViewModel(
        PluginCatalogEntryDto plugin,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        IsCatalogDefinition = false;
        NodeType = plugin.NodeType ?? string.Empty;
        NodeVersion = plugin.NodeVersion ?? string.Empty;
        PackageName = plugin.PackageName;
        PluginId = plugin.PluginId ?? plugin.PackageName;
        PluginVersion = plugin.PluginVersion;
        ProviderType = "user_plugin";
        Category = plugin.Category;
        Enabled = plugin.Enabled;
        DisabledReason = plugin.DisabledReason;
        DisplayName = plugin.DisplayName ?? plugin.PackageName;
        InputPorts = [];
        OutputPorts = [];
        InputTableSlots = [];
        OutputTableSlots = [];
        ExecutionMode = plugin.ExecutionMode ?? string.Empty;
        DefaultTimeoutSeconds = 0;
        RetrySafe = false;
        UiVisibility = "visible";
        ConfigSchema = NodeConfigSchemaParser.Parse(string.Empty, null);
    }

    public bool IsCatalogDefinition { get; }

    public string NodeType { get; }

    public string NodeVersion { get; }

    public string PackageName { get; }

    public string PluginId { get; }

    public string? PluginVersion { get; }

    public string ProviderType { get; }

    public string? Category { get; }

    public bool Enabled { get; }

    public string? DisabledReason { get; }

    public string DisplayName { get; }

    public NodePortDefinitionDto[] InputPorts { get; }

    public NodePortDefinitionDto[] OutputPorts { get; }

    public NodeTableInputSlotDto[] InputTableSlots { get; }

    public NodeTableOutputSlotDto[] OutputTableSlots { get; }

    public string ExecutionMode { get; }

    public int DefaultTimeoutSeconds { get; }

    public bool RetrySafe { get; }

    public string UiVisibility { get; }

    public NodeConfigSchemaParseResult ConfigSchema { get; }

    public NodeConfigSchemaDescriptor? ConfigSchemaDescriptor => ConfigSchema.Schema;

    public DisplayTextFormatter DisplayTextFormatter { get; }

    public bool CanAdd =>
        IsCatalogDefinition
        && Enabled
        && string.Equals(UiVisibility, "visible", System.StringComparison.OrdinalIgnoreCase);

    public bool HasNodeIdentity =>
        !string.IsNullOrWhiteSpace(NodeType)
        && !string.IsNullOrWhiteSpace(NodeVersion);

    public bool HasDisabledReason => !string.IsNullOrWhiteSpace(DisabledReason);

    public string TypeText => HasNodeIdentity
        ? $"{NodeType}@{NodeVersion}"
        : PackageName;

    public string SourceText => DisplayTextFormatter.FormatNodeCatalogSource(
        ProviderType,
        PluginId,
        PluginVersion);

    public string StatusText => DisplayTextFormatter.FormatNodeCatalogStatus(Enabled);

    public string DisabledReasonText =>
        DisplayTextFormatter.FormatNodeCatalogDisabledReason(DisabledReason ?? string.Empty);

    public string DisplayNameText =>
        DisplayTextFormatter.FormatNodeDefinitionDisplayName(
            NodeType,
            string.IsNullOrWhiteSpace(DisplayName) ? NodeType : DisplayName);

    public string InputPortsText => FormatPorts(InputPorts);

    public string OutputPortsText => FormatPorts(OutputPorts);

    public string TimeoutText => DefaultTimeoutSeconds > 0
        ? $"{DefaultTimeoutSeconds}s"
        : "-";

    public string ConfigSchemaSummaryText
    {
        get
        {
            if (ConfigSchema.Schema?.IsSupported != true)
            {
                return DisplayTextFormatter.FormatConfigSchemaUnavailable();
            }

            var fields = ConfigSchema.Schema.Fields;
            if (fields.Count == 0)
            {
                return DisplayTextFormatter.FormatNoConfigFields();
            }

            var fieldNames = string.Join(
                ", ",
                fields.Select(descriptor =>
                    DisplayTextFormatter.FormatNodeConfigFieldTitle(
                        NodeType,
                        descriptor.Name,
                        descriptor.Title)));
            return DisplayTextFormatter.FormatConfigFields(fields.Count, fieldNames);
        }
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(DisplayNameText));
        OnPropertyChanged(nameof(ConfigSchemaSummaryText));
        OnPropertyChanged(nameof(SourceText));
        OnPropertyChanged(nameof(StatusText));
        OnPropertyChanged(nameof(DisabledReasonText));
    }

    private static string FormatPorts(NodePortDefinitionDto[] ports)
    {
        return ports.Length == 0
            ? "-"
            : string.Join(
                ", ",
                ports
                    .OrderBy(port => port.Name)
                    .Select(port => port.Required ? $"{port.Name}*" : port.Name));
    }
}
