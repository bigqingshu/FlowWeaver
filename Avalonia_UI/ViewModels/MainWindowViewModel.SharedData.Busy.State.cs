namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public bool IsDataBusy =>
        IsLoadingTableRefs || IsLoadingSharedPublications || IsLoadingSharedPublicationVersions;
}
