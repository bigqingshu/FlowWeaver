using System;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanExportSelectedWorkflowCore()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && !IsWorkflowBusy;
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
