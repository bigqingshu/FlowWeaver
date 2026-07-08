using System;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private (string? InputPort, string? OutputPort, string? SourceOutputPort) TryGetAutoWirePorts()
    {
        var definition = SelectedNewDraftNodeDefinition;
        if (definition is null)
        {
            return (null, null, null);
        }

        var inputPort = TryGetSingleInputPort(definition.InputPorts);
        if (inputPort is null)
        {
            return (null, null, null);
        }

        return (
            inputPort,
            TryGetPreferredOutputPort(definition.OutputPorts),
            TryGetSourceAutoWireOutputPort());
    }

    private string? TryGetSourceAutoWireOutputPort()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return null;
        }

        var sourceDefinition = FindNodeDefinition(SelectedWorkflowDefinitionNode);
        return sourceDefinition is null
            ? null
            : TryGetPreferredOutputPort(sourceDefinition.OutputPorts);
    }
}
