namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyRecentEventsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(RecentEventsSectionText));
        OnPropertyChanged(nameof(RecentEventsEmptyText));
        OnPropertyChanged(nameof(RecentEventsViewAllText));
        OnPropertyChanged(nameof(RecentEventsToggleText));
    }
}
