using System;
using System.ComponentModel;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public BackgroundRunManagementViewModel BackgroundRunManagement { get; private set; } = null!;

    private void InitializeBackgroundRunManagement(IEngineHostApiClient apiClient)
    {
        BackgroundRunManagement = new BackgroundRunManagementViewModel(
            new BackgroundRunService(apiClient),
            T,
            DisplayTextFormatter);
        BackgroundRunManagement.PropertyChanged += OnBackgroundRunManagementPropertyChanged;
        BackgroundRunManagement.SelectedRunChanged += OnBackgroundRunManagementSelectedRunChanged;
        BackgroundRunManagement.RunStarted += OnBackgroundRunStarted;
        BackgroundRunManagement.RunRetried += OnBackgroundRunRetried;
        BackgroundRunManagement.TablesCleaned += OnBackgroundRunTablesCleaned;
        RefreshBackgroundRunManagementContext();
    }

    private void RefreshBackgroundRunManagementContext()
    {
        if (BackgroundRunManagement is null)
        {
            return;
        }

        BackgroundRunManagement.SetContext(
            BuildSettings(),
            SelectedWorkflow?.WorkflowId,
            CanUseEngineActions);
    }

    private void OnBackgroundRunManagementPropertyChanged(
        object? sender,
        PropertyChangedEventArgs eventArgs)
    {
        if (eventArgs.PropertyName is nameof(BackgroundRunManagementViewModel.IsLoading)
            or nameof(BackgroundRunManagementViewModel.IsStarting)
            or nameof(BackgroundRunManagementViewModel.IsRetrying)
            or nameof(BackgroundRunManagementViewModel.IsCleaningTables))
        {
            IsLoadingRuns = BackgroundRunManagement.IsBusy;
        }

        if (eventArgs.PropertyName == nameof(BackgroundRunManagementViewModel.Message))
        {
            RunMessage = BackgroundRunManagement.Message;
        }

        if (eventArgs.PropertyName == nameof(BackgroundRunManagementViewModel.ErrorMessage))
        {
            RunErrorMessage = BackgroundRunManagement.ErrorMessage;
        }
    }

    private void OnBackgroundRunManagementSelectedRunChanged(
        WorkflowRunListItemViewModel? run)
    {
        if (!ReferenceEquals(SelectedRun, run))
        {
            SelectedRun = run;
        }
    }

    private void OnBackgroundRunStarted(WorkflowRunListItemViewModel run)
    {
        LastStartedRunId = run.WorkflowRunId;
        LastStartedRunStatus = run.Status;
        WorkflowMessage = F(
            "format.started_run_with_status",
            run.WorkflowRunId,
            run.StatusText);
        WorkflowErrorMessage = null;
        ShowWorkflowNotification("workflow.background_run", UiNotificationKind.Success);
    }

    private void OnBackgroundRunRetried(WorkflowRunListItemViewModel run)
    {
        LastStartedRunId = run.WorkflowRunId;
        LastStartedRunStatus = run.Status;
        WorkflowMessage = F(
            "format.started_run_with_status",
            run.WorkflowRunId,
            run.StatusText);
        WorkflowErrorMessage = null;
        ShowWorkflowNotification("workflow.retry_run", UiNotificationKind.Success);
    }

    private async void OnBackgroundRunTablesCleaned(
        string workflowRunId,
        RunTableCleanupResultDto result)
    {
        runMetadataCache.InvalidateRun(workflowRunId);
        if (string.Equals(
                SelectedRun?.WorkflowRunId,
                workflowRunId,
                StringComparison.Ordinal))
        {
            await RefreshTableRefsAsync();
        }

        RunMessage = F(
            "format.background_tables_cleaned",
            result.CleanedCount,
            result.SkippedCount,
            result.FailedCount);
        RunErrorMessage = null;
        ShowNotification(
            "runs.cleanup",
            result.FailedCount > 0 ? UiNotificationKind.Warning : UiNotificationKind.Success,
            RunMessage,
            string.Empty);
    }
}
