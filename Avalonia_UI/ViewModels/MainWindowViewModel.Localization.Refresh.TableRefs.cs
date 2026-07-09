namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyTableRefsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(TableRefsSectionText));
    }
}
