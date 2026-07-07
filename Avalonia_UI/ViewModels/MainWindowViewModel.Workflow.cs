using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private const int WorkflowRunTerminalRefreshAttemptCount = 40;

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

    public bool CanUseImportWorkflowAction => CanImportWorkflowCore();

    public string? ImportWorkflowDisabledReasonText =>
        GetWorkflowCollectionManagementDisabledReason();

    public bool CanUseDeleteSelectedWorkflowAction => CanDeleteSelectedWorkflowCore();

    public bool CanUseExportSelectedWorkflowAction => CanExportSelectedWorkflowCore();

    public string? ExportSelectedWorkflowDisabledReasonText =>
        GetSelectedWorkflowManagementDisabledReason();

    public string? DeleteSelectedWorkflowDisabledReasonText
        => GetSelectedWorkflowManagementDisabledReason();

    private string? GetWorkflowCollectionManagementDisabledReason()
    {
        if (IsWorkflowBusy)
        {
            return T("action.disabled.busy");
        }

        if (!CanUseEngineActions)
        {
            return T("action.disabled.engine_not_connected");
        }

        return null;
    }

    private string? GetSelectedWorkflowManagementDisabledReason()
    {
        if (IsWorkflowBusy)
        {
            return T("action.disabled.busy");
        }

        if (!CanUseEngineActions)
        {
            return T("action.disabled.engine_not_connected");
        }

        if (SelectedWorkflow is null)
        {
            return T("action.disabled.no_workflow_selected");
        }

        if (!IsActiveWorkflowStatus(SelectedWorkflow.Status))
        {
            return T("action.disabled.workflow_not_active");
        }

        return null;
    }

    private bool CanRefreshWorkflows()
    {
        return CanUseEngineActions && !IsWorkflowBusy;
    }

    private bool CanStartSelectedWorkflow()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && !IsWorkflowBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }

    private bool CanPreviewSelectedWorkflowNode()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && !IsWorkflowBusy
            && !IsDataPreviewBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }

    private bool CanCreateTemplateWorkflow()
    {
        return CanUseEngineActions
            && !IsWorkflowBusy
            && !string.IsNullOrWhiteSpace(NewWorkflowName);
    }

    private bool CanImportWorkflowCore()
    {
        return CanUseEngineActions && !IsWorkflowBusy;
    }

    private bool CanDeleteSelectedWorkflowCore()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && !IsWorkflowBusy;
    }

    private bool CanExportSelectedWorkflowCore()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && !IsWorkflowBusy;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshWorkflows))]
    private async Task RefreshWorkflowsAsync()
    {
        IsLoadingWorkflows = true;
        WorkflowMessage = T("workflow.loading");
        WorkflowErrorMessage = null;

        var response = await _apiClient.ListWorkflowsAsync(
            BuildSettings(),
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            var previousWorkflowId = SelectedWorkflow?.WorkflowId;
            Workflows.Clear();
            foreach (var workflow in response.Data)
            {
                Workflows.Add(new WorkflowListItemViewModel(workflow));
            }

            SelectedWorkflow = Workflows.FirstOrDefault(
                workflow => workflow.WorkflowId == previousWorkflowId)
                ?? Workflows.FirstOrDefault();
            WorkflowMessage = F("format.loaded_workflows", Workflows.Count);
            IsLoadingWorkflows = false;
            return;
        }

        WorkflowMessage = T("workflow.refresh_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsLoadingWorkflows = false;
    }

    [RelayCommand(CanExecute = nameof(CanCreateTemplateWorkflow))]
    private async Task CreateTemplateWorkflowAsync()
    {
        var name = NewWorkflowName.Trim();
        if (string.IsNullOrWhiteSpace(name))
        {
            WorkflowMessage = T("workflow.creation_rejected");
            WorkflowErrorMessage = T("workflow.name_required");
            return;
        }

        IsCreatingWorkflow = true;
        WorkflowMessage = F("format.creating_workflow", name);
        WorkflowErrorMessage = null;

        using var definition = TemplateWorkflowDefinitions.CreateGeneratedTable(
            T("workflow.template.generate_rows_display_name"),
            T("workflow.template.keep_amount_gt_one_display_name"));
        var response = await _apiClient.CreateWorkflowAsync(
            BuildSettings(),
            name,
            definition.RootElement,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            WorkflowMessage = F("format.created_workflow", response.Data.Name);
            IsCreatingWorkflow = false;
            await RefreshWorkflowsSelectingAsync(response.Data.WorkflowId);
            return;
        }

        WorkflowMessage = T("workflow.creation_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsCreatingWorkflow = false;
    }

    [RelayCommand(CanExecute = nameof(CanImportWorkflowCore))]
    private async Task ImportWorkflowAsync()
    {
        IsImportingWorkflow = true;
        WorkflowMessage = T("workflow.importing");
        WorkflowErrorMessage = null;

        try
        {
            var fileResult = await _workflowImportFileService.OpenWorkflowImportAsync(
                _shutdown.Token);
            if (fileResult.Cancelled)
            {
                WorkflowMessage = T("workflow.import_cancelled");
                WorkflowErrorMessage = null;
                return;
            }

            if (!fileResult.Opened || fileResult.Content is null)
            {
                WorkflowMessage = T("workflow.import_failed");
                WorkflowErrorMessage = fileResult.ErrorMessage;
                return;
            }

            var importResult = WorkflowImportDocumentReader.Read(fileResult.Content);
            if (!importResult.Succeeded ||
                importResult.Name is null ||
                importResult.ErrorMessageKey is not null)
            {
                WorkflowMessage = T("workflow.import_failed");
                WorkflowErrorMessage = T(
                    importResult.ErrorMessageKey ?? "workflow.import_invalid_document");
                return;
            }

            var response = await _apiClient.CreateWorkflowAsync(
                BuildSettings(),
                importResult.Name,
                importResult.Definition,
                _shutdown.Token);

            if (response.Ok && response.Data is not null)
            {
                var importedWorkflowId = response.Data.WorkflowId;
                var importedWorkflowName = response.Data.Name;
                await RefreshWorkflowsSelectingAsync(importedWorkflowId);
                if (!HasWorkflowError)
                {
                    WorkflowMessage = F("format.imported_workflow", importedWorkflowName);
                }

                return;
            }

            WorkflowMessage = T("workflow.import_failed");
            WorkflowErrorMessage = DescribeError(response);
        }
        finally
        {
            IsImportingWorkflow = false;
        }
    }

    [RelayCommand(CanExecute = nameof(CanDeleteSelectedWorkflowCore))]
    private async Task DeleteSelectedWorkflowAsync()
    {
        if (SelectedWorkflow is null)
        {
            return;
        }

        var workflowId = SelectedWorkflow.WorkflowId;
        var workflowName = SelectedWorkflow.Name;
        IsDeletingWorkflow = true;
        WorkflowMessage = F("format.deleting_workflow", workflowName);
        WorkflowErrorMessage = null;

        var response = await _apiClient.DeleteWorkflowAsync(
            BuildSettings(),
            workflowId,
            _shutdown.Token);

        IsDeletingWorkflow = false;

        if (response.Ok)
        {
            var workflow = Workflows.FirstOrDefault(
                item => item.WorkflowId == workflowId);
            if (workflow is not null)
            {
                Workflows.Remove(workflow);
            }

            if (SelectedWorkflow?.WorkflowId == workflowId)
            {
                SelectedWorkflow = null;
            }

            WorkflowMessage = F("format.deleted_workflow", workflowName);
            WorkflowErrorMessage = null;
            return;
        }

        WorkflowMessage = T("workflow.delete_failed");
        WorkflowErrorMessage = DescribeError(response);
    }

    [RelayCommand(CanExecute = nameof(CanExportSelectedWorkflowCore))]
    private async Task ExportSelectedWorkflowAsync()
    {
        if (SelectedWorkflow is null)
        {
            return;
        }

        var workflowId = SelectedWorkflow.WorkflowId;
        var workflowName = SelectedWorkflow.Name;
        IsExportingWorkflow = true;
        WorkflowMessage = F("format.exporting_workflow", workflowName);
        WorkflowErrorMessage = null;

        try
        {
            var response = await _apiClient.GetWorkflowAsync(
                BuildSettings(),
                workflowId,
                _shutdown.Token);

            if (!response.Ok || response.Data is null)
            {
                WorkflowMessage = T("workflow.export_failed");
                WorkflowErrorMessage = DescribeError(response);
                return;
            }

            var content = WorkflowExportDocumentBuilder.Serialize(
                response.Data,
                DateTimeOffset.UtcNow);
            var result = await _workflowExportFileService.SaveWorkflowExportAsync(
                WorkflowExportDocumentBuilder.SuggestedFileName(response.Data),
                content,
                _shutdown.Token);

            if (result.Cancelled)
            {
                WorkflowMessage = T("workflow.export_cancelled");
                WorkflowErrorMessage = null;
                return;
            }

            if (!result.Saved)
            {
                WorkflowMessage = T("workflow.export_failed");
                WorkflowErrorMessage = result.ErrorMessage;
                return;
            }

            WorkflowMessage = F("format.exported_workflow", response.Data.Name);
            WorkflowErrorMessage = null;
        }
        finally
        {
            IsExportingWorkflow = false;
        }
    }

    private async Task RefreshWorkflowsAfterHealthyConnectionAsync()
    {
        if (Workflows.Count > 0 || !CanRefreshWorkflows())
        {
            return;
        }

        await RefreshWorkflowsAsync();
        if (CanLoadSelectedWorkflowDefinition())
        {
            await LoadSelectedWorkflowDefinitionAsync();
        }
    }

    [RelayCommand(CanExecute = nameof(CanStartSelectedWorkflow))]
    private async Task StartSelectedWorkflowAsync()
    {
        if (SelectedWorkflow is null)
        {
            return;
        }

        IsStartingWorkflow = true;
        WorkflowMessage = F("format.starting_workflow", SelectedWorkflow.Name);
        WorkflowErrorMessage = null;
        LastStartedRunId = null;
        LastStartedRunStatus = null;

        if (IsWorkflowDefinitionDraftDirty)
        {
            WorkflowMessage = T("workflow.saving_draft_before_run");
            if (!await EnsureWorkflowDefinitionDraftSavedForRunAsync())
            {
                WorkflowMessage = T("workflow.start_failed");
                WorkflowErrorMessage = WorkflowDefinitionValidationErrorMessage;
                ShowWorkflowNotification("workflow.run", UiNotificationKind.Error);
                IsStartingWorkflow = false;
                return;
            }
        }

        if (SelectedWorkflow is null)
        {
            WorkflowMessage = T("workflow.start_failed");
            WorkflowErrorMessage = T("definition.load_before_saving");
            ShowWorkflowNotification("workflow.run", UiNotificationKind.Error);
            IsStartingWorkflow = false;
            return;
        }

        WorkflowMessage = F("format.starting_workflow", SelectedWorkflow.Name);
        var response = await _apiClient.StartWorkflowRunAsync(
            BuildSettings(),
            SelectedWorkflow.WorkflowId,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            LastStartedRunId = response.Data.WorkflowRunId;
            LastStartedRunStatus = response.Data.Status;
            WorkflowMessage =
                F(
                    "format.started_run_with_status",
                    response.Data.WorkflowRunId,
                    response.Data.Status);
            ShowWorkflowNotification("workflow.run", UiNotificationKind.Success);
            IsStartingWorkflow = false;
            await TrackWorkflowRunUntilTerminalAsync(response.Data.WorkflowRunId);
            await SelectLatestReadableOutputNodeForRunAsync(response.Data.WorkflowRunId);
            if (CanRefreshSelectedWorkflowNodeDataPreview())
            {
                await RefreshSelectedWorkflowNodeDataPreviewAsync();
            }

            return;
        }

        WorkflowMessage = T("workflow.start_failed");
        WorkflowErrorMessage = DescribeError(response);
        ShowWorkflowNotification("workflow.run", UiNotificationKind.Error);
        IsStartingWorkflow = false;
    }

    [RelayCommand(CanExecute = nameof(CanPreviewSelectedWorkflowNode))]
    private async Task PreviewSelectedWorkflowNodeAsync()
    {
        if (SelectedWorkflow is null || SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var targetNodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        IsStartingWorkflow = true;
        WorkflowMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        WorkflowErrorMessage = null;
        DataPreviewMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        DataPreviewErrorMessage = null;
        LastStartedRunId = null;
        LastStartedRunStatus = null;

        if (IsWorkflowDefinitionDraftDirty)
        {
            WorkflowMessage = T("workflow.saving_draft_before_preview");
            DataPreviewMessage = T("workflow.saving_draft_before_preview");
            if (!await EnsureWorkflowDefinitionDraftSavedForRunAsync())
            {
                WorkflowMessage = T("workflow.start_failed");
                WorkflowErrorMessage = WorkflowDefinitionValidationErrorMessage;
                DataPreviewMessage = T("data_preview.preview_failed");
                DataPreviewErrorMessage = WorkflowDefinitionValidationErrorMessage;
                ShowWorkflowNotification("workflow.preview", UiNotificationKind.Error);
                ShowDataPreviewNotification(UiNotificationKind.Error);
                IsStartingWorkflow = false;
                return;
            }

            SelectWorkflowDefinitionDraftNode(targetNodeInstanceId);
        }

        if (SelectedWorkflow is null ||
            SelectedWorkflowDefinitionNode is null ||
            !string.Equals(
                SelectedWorkflowDefinitionNode.NodeInstanceId,
                targetNodeInstanceId,
                StringComparison.Ordinal))
        {
            WorkflowMessage = T("workflow.start_failed");
            WorkflowErrorMessage = T("action.disabled.workflow_node_missing");
            DataPreviewMessage = T("data_preview.preview_failed");
            DataPreviewErrorMessage = T("action.disabled.workflow_node_missing");
            ShowWorkflowNotification("workflow.preview", UiNotificationKind.Error);
            ShowDataPreviewNotification(UiNotificationKind.Error);
            IsStartingWorkflow = false;
            return;
        }

        WorkflowMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        DataPreviewMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        var response = await _apiClient.StartWorkflowRunAsync(
            BuildSettings(),
            SelectedWorkflow.WorkflowId,
            "preview_to_node",
            targetNodeInstanceId,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            LastStartedRunId = response.Data.WorkflowRunId;
            LastStartedRunStatus = response.Data.Status;
            WorkflowMessage =
                F(
                    "format.started_preview_run_with_status",
                    response.Data.WorkflowRunId,
                    response.Data.Status,
                    targetNodeInstanceId);
            ShowWorkflowNotification("workflow.preview", UiNotificationKind.Success);
            IsStartingWorkflow = false;
            await RefreshSelectedWorkflowNodeDataPreviewAfterRunStartAsync(response.Data.WorkflowRunId);

            return;
        }

        WorkflowMessage = T("workflow.start_failed");
        WorkflowErrorMessage = DescribeError(response);
        DataPreviewMessage = T("data_preview.preview_failed");
        DataPreviewErrorMessage = DescribeError(response);
        ShowWorkflowNotification("workflow.preview", UiNotificationKind.Error);
        ShowDataPreviewNotification(UiNotificationKind.Error);
        IsStartingWorkflow = false;
    }

    private async Task TrackWorkflowRunUntilTerminalAsync(string workflowRunId)
    {
        for (var attempt = 0; attempt < WorkflowRunTerminalRefreshAttemptCount; attempt++)
        {
            await LoadRunsAsync(workflowRunId);
            if (SelectedRun is not null && IsTerminalRunStatus(SelectedRun.Status))
            {
                return;
            }

            if (attempt + 1 < WorkflowRunTerminalRefreshAttemptCount)
            {
                await _dataPreviewRunRefreshDelay(_shutdown.Token);
            }
        }
    }

    private async Task RefreshWorkflowsSelectingAsync(string workflowId)
    {
        IsLoadingWorkflows = true;
        WorkflowMessage = T("workflow.refreshing");
        WorkflowErrorMessage = null;

        var response = await _apiClient.ListWorkflowsAsync(
            BuildSettings(),
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            Workflows.Clear();
            foreach (var workflow in response.Data)
            {
                Workflows.Add(new WorkflowListItemViewModel(workflow));
            }

            SelectedWorkflow = Workflows.FirstOrDefault(workflow => workflow.WorkflowId == workflowId)
                ?? Workflows.FirstOrDefault();
            WorkflowMessage = F("format.loaded_workflows", Workflows.Count);
            IsLoadingWorkflows = false;
            return;
        }

        WorkflowMessage = T("workflow.refresh_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsLoadingWorkflows = false;
    }

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

internal static class TemplateWorkflowDefinitions
{
    public static JsonDocument CreateGeneratedTable(
        string generateRowsDisplayName,
        string keepAmountGreaterThanOneDisplayName)
    {
        var definition = new
        {
            schema_version = "1.0",
            nodes = new object[]
            {
                new
                {
                    node_instance_id = "generate",
                    node_type = "GenerateTestTableNode",
                    node_version = "1.0",
                    display_name = generateRowsDisplayName,
                    config = new
                    {
                        rows = 3,
                        columns = new[] { "row_id", "amount" },
                        seed = 0,
                    },
                },
                new
                {
                    node_instance_id = "filter",
                    node_type = "FilterRowsNode",
                    node_version = "1.0",
                    display_name = keepAmountGreaterThanOneDisplayName,
                    config = new
                    {
                        field = "amount",
                        @operator = "GT",
                        value = 1.0,
                    },
                },
            },
            connections = new[]
            {
                new
                {
                    connection_id = "generate_to_filter",
                    source_node_id = "generate",
                    source_port = "out",
                    target_node_id = "filter",
                    target_port = "in",
                },
            },
        };

        return JsonSerializer.SerializeToDocument(definition, FlowWeaverJson.Options);
    }
}
