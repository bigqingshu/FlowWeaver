namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifySharedPublicationsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(ShareText));
        OnPropertyChanged(nameof(ShareNameWatermarkText));
        OnPropertyChanged(nameof(VersionsText));
    }
}
