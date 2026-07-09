using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnWorkflowDefinitionDraftStructureChanged(
        WorkflowDefinitionDraftStructure? value)
    {
        NotifyWorkflowDefinitionDraftStructurePresentationChanged();
        if (SelectedRuntimeOptionsNode is not null &&
            !WorkflowDefinitionDraftNodes.Contains(SelectedRuntimeOptionsNode))
        {
            SelectedRuntimeOptionsNode = null;
        }

        NotifyWorkflowDefinitionNodeActionCommandsChanged();
    }
}
