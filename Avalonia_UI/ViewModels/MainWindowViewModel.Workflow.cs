using System.Collections.ObjectModel;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isLoadingWorkflows;

    [ObservableProperty]
    private bool isStartingWorkflow;

    [ObservableProperty]
    private string newWorkflowName = "Generated table workflow";

    [ObservableProperty]
    private bool isCreatingWorkflow;

    [ObservableProperty]
    private bool isImportingWorkflow;

    [ObservableProperty]
    private bool isDeletingWorkflow;

    [ObservableProperty]
    private bool isExportingWorkflow;

    [ObservableProperty]
    private WorkflowListItemViewModel? selectedWorkflow;

    [ObservableProperty]
    private string workflowMessage = "No workflows loaded.";

    [ObservableProperty]
    private string? workflowErrorMessage;

    [ObservableProperty]
    private string? lastStartedRunId;

    [ObservableProperty]
    private string? lastStartedRunStatus;

    public ObservableCollection<WorkflowListItemViewModel> Workflows { get; } = new();

    public bool HasWorkflowError => !string.IsNullOrWhiteSpace(WorkflowErrorMessage);

    public bool IsWorkflowBusy =>
        IsLoadingWorkflows
        || IsStartingWorkflow
        || IsCreatingWorkflow
        || IsImportingWorkflow
        || IsDeletingWorkflow
        || IsExportingWorkflow;

    public bool HasLastStartedRun => !string.IsNullOrWhiteSpace(LastStartedRunId);

    partial void OnIsLoadingWorkflowsChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnIsStartingWorkflowChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnNewWorkflowNameChanged(string value)
    {
        CreateTemplateWorkflowCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsCreatingWorkflowChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnIsImportingWorkflowChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnIsDeletingWorkflowChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnIsExportingWorkflowChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

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
            originalWorkflowDefinitionJson = string.Empty;
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

    partial void OnWorkflowErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasWorkflowError));
    }

    partial void OnLastStartedRunIdChanged(string? value)
    {
        OnPropertyChanged(nameof(HasLastStartedRun));
    }

    private void NotifyWorkflowCommandStateChanged()
    {
        OnPropertyChanged(nameof(IsWorkflowBusy));
        RefreshWorkflowsCommand.NotifyCanExecuteChanged();
        CreateTemplateWorkflowCommand.NotifyCanExecuteChanged();
        ImportWorkflowCommand.NotifyCanExecuteChanged();
        ExportSelectedWorkflowCommand.NotifyCanExecuteChanged();
        DeleteSelectedWorkflowCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(CanUseImportWorkflowAction));
        OnPropertyChanged(nameof(ImportWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(CanUseExportSelectedWorkflowAction));
        OnPropertyChanged(nameof(ExportSelectedWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(CanUseDeleteSelectedWorkflowAction));
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDisabledReasonText));
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    private static bool IsActiveWorkflowStatus(string? status)
    {
        return status == "ACTIVE";
    }
}
