using System.Collections.ObjectModel;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

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

    private bool CanRefreshSharedPublicationVersions()
    {
        return CanUseEngineActions
            && !IsLoadingSharedPublicationVersions
            && (NormalizeFilter(SharedPublicationVersionShareNameFilter) is not null
                || SelectedSharedPublication is not null);
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSharedPublicationVersions))]
    private async Task RefreshSharedPublicationVersionsAsync()
    {
        var shareName = NormalizeFilter(SharedPublicationVersionShareNameFilter)
            ?? SelectedSharedPublication?.ShareName;
        if (string.IsNullOrWhiteSpace(shareName))
        {
            SharedPublicationVersionMessage = T("data.shared_publication_versions_rejected");
            SharedPublicationVersionErrorMessage =
                T("data.share_name_required_for_versions");
            return;
        }

        if (!TryParseLimit(
            SharedPublicationVersionLimitFilter,
            T("data.shared_publication_version_limit_label"),
            out var limit,
            out var error))
        {
            SharedPublicationVersionMessage = T("data.shared_publication_versions_rejected");
            SharedPublicationVersionErrorMessage = error;
            return;
        }

        var requestVersion = ++sharedPublicationVersionsLoadVersion;
        IsLoadingSharedPublicationVersions = true;
        SharedPublicationVersionMessage = F("format.loading_versions_for", shareName);
        SharedPublicationVersionErrorMessage = null;

        try
        {
            var response = await _apiClient.ListSharedPublicationVersionsAsync(
                BuildSettings(),
                shareName,
                limit,
                _shutdown.Token);

            if (requestVersion != sharedPublicationVersionsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                SharedPublicationVersions.Clear();
                foreach (var publication in response.Data)
                {
                    SharedPublicationVersions.Add(
                        new SharedPublicationListItemViewModel(publication, DisplayTextFormatter));
                }

                SharedPublicationVersionMessage =
                    F(
                        "format.loaded_shared_publication_versions",
                        SharedPublicationVersions.Count,
                        shareName);
                return;
            }

            SharedPublicationVersionMessage = T("data.shared_publication_versions_refresh_failed");
            SharedPublicationVersionErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == sharedPublicationVersionsLoadVersion)
            {
                IsLoadingSharedPublicationVersions = false;
            }
        }
    }

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
