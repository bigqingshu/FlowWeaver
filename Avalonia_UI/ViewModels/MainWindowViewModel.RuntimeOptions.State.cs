using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RefreshRuntimeOptionsDraftState()
    {
        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        var draft = readResult.Succeeded ? readResult.Draft : new RuntimeOptionsDraft();
        var workflowFieldState =
            RuntimeOptionsDraftStateMapper.ToWorkflowFieldState(draft.Workflow);

        ApplyRuntimeOptionsWorkflowDraftFieldState(workflowFieldState);
        RuntimeOptionsNodeOverrideCount = draft.NodeOverrides.Count;
        RuntimeOptionsEditorErrorMessage =
            readResult.Succeeded
                ? null
                : LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);

        if (SelectedRuntimeOptionsNode is not null &&
            !WorkflowDefinitionDraftNodes.Contains(SelectedRuntimeOptionsNode))
        {
            SelectedRuntimeOptionsNode = null;
        }

        RefreshSelectedRuntimeOptionsNodeDraftState(draft);
        NotifyRuntimeOptionsSummaryChanged();
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
    }

}
