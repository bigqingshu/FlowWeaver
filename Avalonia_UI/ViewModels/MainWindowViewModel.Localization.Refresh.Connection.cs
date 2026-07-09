namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyConnectionLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(ConnectionBaseUrlText));
        OnPropertyChanged(nameof(ConnectionTokenText));
        OnPropertyChanged(nameof(ConnectionStatusText));
        OnPropertyChanged(nameof(ConnectionEventsText));
        OnPropertyChanged(nameof(CheckConnectionText));
        OnPropertyChanged(nameof(StreamText));
        OnPropertyChanged(nameof(StopText));
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
    }
}
