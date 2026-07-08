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

    private bool CanDeleteSelectedWorkflowCore()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && !IsWorkflowBusy;
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
}
