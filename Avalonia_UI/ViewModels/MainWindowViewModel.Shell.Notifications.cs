namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyShellNavigationItemsChanged()
    {
        OnPropertyChanged(nameof(ShellNavigationItems));
        OnPropertyChanged(nameof(WorkflowsNavigationItem));
        OnPropertyChanged(nameof(DataPreviewNavigationItem));
        OnPropertyChanged(nameof(RunsNavigationItem));
        OnPropertyChanged(nameof(DataNavigationItem));
        OnPropertyChanged(nameof(LogsNavigationItem));
        OnPropertyChanged(nameof(SettingsNavigationItem));
        OnPropertyChanged(nameof(SelectedShellNavigationItem));
        OnPropertyChanged(nameof(SelectedShellPageContentKey));
        OnPropertyChanged(nameof(SelectedShellPageIndex));
    }
}
