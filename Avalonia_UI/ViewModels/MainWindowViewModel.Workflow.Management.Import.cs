using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanImportWorkflowCore()
    {
        return CanUseEngineActions && !IsWorkflowBusy;
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
}
