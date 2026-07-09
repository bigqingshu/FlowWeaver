namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyRunSelectionActionStateChanged()
    {
        OnPropertyChanged(nameof(CanUseCancelSelectedRunAction));
        OnPropertyChanged(nameof(CancelSelectedRunDisabledReasonText));
    }

    private void NotifyRunMonitorActionStateChanged()
    {
        RefreshRunsCommand.NotifyCanExecuteChanged();
        CancelSelectedRunCommand.NotifyCanExecuteChanged();
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
    }
}
