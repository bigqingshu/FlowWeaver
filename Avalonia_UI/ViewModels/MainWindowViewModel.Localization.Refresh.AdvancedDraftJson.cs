namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyAdvancedDraftJsonLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(DraftJsonSectionText));
        OnPropertyChanged(nameof(ShowAdvancedDraftJsonText));
        OnPropertyChanged(nameof(ValidateText));
        OnPropertyChanged(nameof(SaveText));
    }
}
