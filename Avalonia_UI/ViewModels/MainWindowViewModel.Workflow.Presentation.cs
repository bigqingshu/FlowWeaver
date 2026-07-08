namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public bool HasWorkflowError => !string.IsNullOrWhiteSpace(WorkflowErrorMessage);

    public bool IsWorkflowBusy =>
        IsLoadingWorkflows
        || IsStartingWorkflow
        || IsCreatingWorkflow
        || IsImportingWorkflow
        || IsDeletingWorkflow
        || IsExportingWorkflow;

    public bool HasLastStartedRun => !string.IsNullOrWhiteSpace(LastStartedRunId);
}
