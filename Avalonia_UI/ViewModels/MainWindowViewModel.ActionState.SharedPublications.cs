namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifySharedPublicationActionStateChanged()
    {
        RefreshSharedPublicationsCommand.NotifyCanExecuteChanged();
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }
}
