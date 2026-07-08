namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifySharedDataLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(TableRefsSectionText));
        OnPropertyChanged(nameof(ShareText));
        OnPropertyChanged(nameof(ShareNameWatermarkText));
        OnPropertyChanged(nameof(VersionsText));
    }
}
