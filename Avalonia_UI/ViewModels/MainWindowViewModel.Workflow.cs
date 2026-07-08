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

    private static bool IsActiveWorkflowStatus(string? status)
    {
        return status == "ACTIVE";
    }
}
