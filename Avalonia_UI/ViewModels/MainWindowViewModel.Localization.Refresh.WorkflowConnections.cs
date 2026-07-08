namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyWorkflowConnectionsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(ConnectionsSectionText));
        OnPropertyChanged(nameof(ShowConnectionsText));
        OnPropertyChanged(nameof(AddConnectionText));
        OnPropertyChanged(nameof(DeleteConnectionText));
        OnPropertyChanged(nameof(ConnectionIdText));
        OnPropertyChanged(nameof(SourceNodeText));
        OnPropertyChanged(nameof(SourcePortText));
        OnPropertyChanged(nameof(TargetNodeText));
        OnPropertyChanged(nameof(TargetPortText));
    }
}
