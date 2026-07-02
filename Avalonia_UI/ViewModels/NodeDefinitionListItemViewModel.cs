using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class NodeDefinitionListItemViewModel
{
    public NodeDefinitionListItemViewModel(NodeDefinitionDto definition)
    {
        NodeType = definition.NodeType;
        NodeVersion = definition.NodeVersion;
        DisplayName = definition.DisplayName;
        InputPorts = definition.InputPorts;
        OutputPorts = definition.OutputPorts;
        ExecutionMode = definition.ExecutionMode;
        DefaultTimeoutSeconds = definition.DefaultTimeoutSeconds;
        RetrySafe = definition.RetrySafe;
        UiVisibility = definition.UiVisibility;
    }

    public string NodeType { get; }

    public string NodeVersion { get; }

    public string DisplayName { get; }

    public NodePortDefinitionDto[] InputPorts { get; }

    public NodePortDefinitionDto[] OutputPorts { get; }

    public string ExecutionMode { get; }

    public int DefaultTimeoutSeconds { get; }

    public bool RetrySafe { get; }

    public string UiVisibility { get; }

    public string TypeText => $"{NodeType}@{NodeVersion}";

    public string DisplayNameText =>
        string.IsNullOrWhiteSpace(DisplayName) ? NodeType : DisplayName;

    public string InputPortsText => FormatPorts(InputPorts);

    public string OutputPortsText => FormatPorts(OutputPorts);

    public string TimeoutText => $"{DefaultTimeoutSeconds}s";

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
