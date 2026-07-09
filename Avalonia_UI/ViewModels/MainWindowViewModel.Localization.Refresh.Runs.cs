namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyRunsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(RunsSectionText));
        OnPropertyChanged(nameof(CancelText));
        OnPropertyChanged(nameof(CancelConfirmTitleText));
        OnPropertyChanged(nameof(CancelConfirmMessageText));
        OnPropertyChanged(nameof(NodeRunsSectionText));
    }
}
