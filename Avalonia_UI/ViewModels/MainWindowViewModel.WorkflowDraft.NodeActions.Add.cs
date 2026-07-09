using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanAddWorkflowDefinitionDraftNode))]
    private void AddWorkflowDefinitionDraftNode()
    {
        var autoWirePorts = TryGetAutoWirePorts();
        if (!TryReadNewDraftNodeConfigJson(out var config))
        {
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.AddNode(
            WorkflowDefinitionDraftJson,
            NewDraftNodeInstanceId,
            NewDraftNodeType,
            NewDraftNodeVersion,
            NewDraftNodeDisplayName,
            config,
            SelectedWorkflowDefinitionNode?.NodeInstanceId,
            autoWirePorts.InputPort,
            autoWirePorts.OutputPort,
            autoWirePorts.SourceOutputPort);
        if (!patchResult.Succeeded)
        {
            ApplyWorkflowDefinitionDraftAddNodeFailure(patchResult);
            return;
        }

        ApplyWorkflowDefinitionDraftAddNodeSuccess(patchResult);
    }
}
