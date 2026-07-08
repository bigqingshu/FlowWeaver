using System;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
