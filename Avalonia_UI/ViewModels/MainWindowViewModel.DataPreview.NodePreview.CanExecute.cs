namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshSelectedWorkflowNodeDataPreview()
    {
        return CanUseEngineActions
            && SelectedRun is not null
            && SelectedWorkflowDefinitionNode is not null
            && !IsLoadingDataPreview;
    }

    private bool CanShowDataPreviewDetails()
    {
        return CanUseEngineActions
            && !string.IsNullOrWhiteSpace(dataPreviewSourceTableRefId)
            && !IsLoadingDataPreviewWorkbench;
    }
}
