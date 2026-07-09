namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyDataPreviewActionStateChanged()
    {
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }
}
