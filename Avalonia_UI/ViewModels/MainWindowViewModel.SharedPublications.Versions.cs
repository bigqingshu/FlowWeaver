using System.Collections.ObjectModel;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int sharedPublicationVersionsLoadVersion;

    [ObservableProperty]
    private string sharedPublicationVersionShareNameFilter = string.Empty;

    [ObservableProperty]
    private string sharedPublicationVersionLimitFilter = "100";

    [ObservableProperty]
    private bool isLoadingSharedPublicationVersions;

    [ObservableProperty]
    private string sharedPublicationVersionMessage =
        "Select or enter a share name to load versions.";

    [ObservableProperty]
    private string? sharedPublicationVersionErrorMessage;

    public ObservableCollection<SharedPublicationListItemViewModel> SharedPublicationVersions { get; } =
        new();

    public bool HasSharedPublicationVersionError =>
        !string.IsNullOrWhiteSpace(SharedPublicationVersionErrorMessage);

    partial void OnSelectedSharedPublicationChanged(SharedPublicationListItemViewModel? value)
    {
        sharedPublicationVersionsLoadVersion++;
        IsLoadingSharedPublicationVersions = false;
        SharedPublicationVersions.Clear();
        SharedPublicationVersionMessage = string.Empty;
        SharedPublicationVersionErrorMessage = null;

        if (value is not null)
        {
            SharedPublicationVersionShareNameFilter = value.ShareName;
        }

        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSharedPublicationVersionShareNameFilterChanged(string value)
    {
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsLoadingSharedPublicationVersionsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataBusy));
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSharedPublicationVersionErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasSharedPublicationVersionError));
    }
}
