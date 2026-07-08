namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyWorkflowListAndRunsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(WorkflowsSectionText));
        OnPropertyChanged(nameof(RefreshText));
        OnPropertyChanged(nameof(CloseText));
        OnPropertyChanged(nameof(RunText));
        OnPropertyChanged(nameof(WorkflowRunGuardText));
        OnPropertyChanged(nameof(CreateText));
        OnPropertyChanged(nameof(ImportWorkflowText));
        OnPropertyChanged(nameof(ExportWorkflowText));
        OnPropertyChanged(nameof(DeleteWorkflowText));
        OnPropertyChanged(nameof(DeleteWorkflowConfirmTitleText));
        OnPropertyChanged(nameof(DeleteWorkflowConfirmMessageText));
        OnPropertyChanged(nameof(CanUseImportWorkflowAction));
        OnPropertyChanged(nameof(ImportWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(CanUseExportSelectedWorkflowAction));
        OnPropertyChanged(nameof(ExportSelectedWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(CanUseDeleteSelectedWorkflowAction));
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(WorkflowNameWatermarkText));
        OnPropertyChanged(nameof(RunsSectionText));
        OnPropertyChanged(nameof(CancelText));
        OnPropertyChanged(nameof(CancelConfirmTitleText));
        OnPropertyChanged(nameof(CancelConfirmMessageText));
        OnPropertyChanged(nameof(NodeRunsSectionText));
    }
}
