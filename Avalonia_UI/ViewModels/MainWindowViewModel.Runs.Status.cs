namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyRunCommandStateChanged()
    {
        OnPropertyChanged(nameof(IsRunBusy));
        NotifyEngineActionStateChanged();
        RefreshRunsCommand.NotifyCanExecuteChanged();
    }

    private static bool IsCancelableRunStatus(string? status)
    {
        return status == "RUNNING";
    }

    private static bool IsTerminalRunStatus(string? status)
    {
        return status is "SUCCEEDED" or "FAILED" or "CANCELLED" or "ABORTED";
    }
}
