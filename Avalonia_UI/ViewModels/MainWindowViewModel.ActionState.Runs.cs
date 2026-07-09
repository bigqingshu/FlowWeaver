namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyRunMonitorActionStateChanged()
    {
        RefreshRunsCommand.NotifyCanExecuteChanged();
        CancelSelectedRunCommand.NotifyCanExecuteChanged();
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
    }
}
