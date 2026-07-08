namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static bool IsActiveWorkflowStatus(string? status)
    {
        return status == "ACTIVE";
    }

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

}
