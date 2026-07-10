using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private WorkflowListItemViewModel? selectedWorkflow;

    partial void OnSelectedWorkflowChanged(WorkflowListItemViewModel? value)
    {
        workflowDefinitionLoadVersion++;
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        LoadSelectedWorkflowDefinitionCommand.NotifyCanExecuteChanged();
        ExportSelectedWorkflowCommand.NotifyCanExecuteChanged();
        DeleteSelectedWorkflowCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(CanUseExportSelectedWorkflowAction));
        OnPropertyChanged(nameof(ExportSelectedWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(CanUseDeleteSelectedWorkflowAction));
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDisabledReasonText));
        Runs.Clear();
        SelectedRun = null;
        RunMessage = value is null
            ? T("runs.no_workflow_selected")
            : F("format.selected_workflow_refresh_runs", value.Name);
        RunErrorMessage = null;
        if (WorkflowDefinitionDetail?.WorkflowId != value?.WorkflowId)
        {
            WorkflowDefinitionDetail = null;
            SelectedWorkflowDefinitionNode = null;
            workflowDefinitionDraftDocumentState.AcceptOriginalDefinition(string.Empty);
            WorkflowDefinitionDraftJson = string.Empty;
            IsWorkflowDefinitionDraftDirty = false;
            HasWorkflowDefinitionRevisionConflict = false;
            WorkflowDefinitionMessage = value is null
                ? T("status.select_workflow_definition")
                : F("format.selected_workflow_load_definition", value.Name);
        }

        WorkflowDefinitionErrorMessage = null;
        WorkflowDefinitionValidationMessage = value is null
            ? T("status.load_definition_to_edit")
            : T("definition.load_before_editing");
        WorkflowDefinitionValidationErrorMessage = null;
        if (value is not null
            && Workflows.Contains(value)
            && !IsLoadingWorkflows
            && CanLoadSelectedWorkflowDefinition())
        {
            LoadSelectedWorkflowDefinitionCommand.Execute(null);
        }
    }
}
