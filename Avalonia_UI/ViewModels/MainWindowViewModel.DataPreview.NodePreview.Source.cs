namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ClearDataPreviewSourceIfNoPreviewRows()
    {
        if (HasDataPreviewColumns || HasDataPreviewRows)
        {
            return;
        }

        dataPreviewSourceWorkflowRunId = null;
        dataPreviewSourceNodeInstanceId = null;
        dataPreviewSourceLogicalTableId = null;
        dataPreviewSourceTableRefId = null;
        dataPreviewSourceRunMode = null;
        dataPreviewSourceTargetNodeInstanceId = null;
        OnPropertyChanged(nameof(DataPreviewSourceText));
    }

    private void UpdateDataPreviewSource(
        string workflowRunId,
        string nodeInstanceId,
        string logicalTableId,
        string tableRefId,
        string? runMode,
        string? targetNodeInstanceId)
    {
        dataPreviewSourceWorkflowRunId = workflowRunId;
        dataPreviewSourceNodeInstanceId = nodeInstanceId;
        dataPreviewSourceLogicalTableId = logicalTableId;
        dataPreviewSourceTableRefId = tableRefId;
        dataPreviewSourceRunMode = runMode;
        dataPreviewSourceTargetNodeInstanceId = targetNodeInstanceId;
        OnPropertyChanged(nameof(DataPreviewSourceText));
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
    }
}
