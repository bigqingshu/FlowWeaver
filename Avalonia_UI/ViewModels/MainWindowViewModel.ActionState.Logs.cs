namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyRuntimeEventLogActionStateChanged()
    {
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
    }
}
