namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyDataPreviewWorkbenchRowsChanged()
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchColumns));
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchRows));
        OnPropertyChanged(nameof(DataPreviewWorkbenchPageText));
        CopyDataPreviewWorkbenchTsvCommand.NotifyCanExecuteChanged();
    }
}
