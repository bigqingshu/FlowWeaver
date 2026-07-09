using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int sharedPublicationsLoadVersion;

    [ObservableProperty]
    private SharedPublicationListItemViewModel? selectedSharedPublication;

    public bool IsDataBusy =>
        IsLoadingTableRefs || IsLoadingSharedPublications || IsLoadingSharedPublicationVersions;

    public string ShareText => T("data.share");

    public string ShareNameWatermarkText => T("data.share_name_watermark");

    public string VersionsText => T("data.versions");
}
